import pytest
import sqlalchemy as sa

from colandr import models


class TestUser:
    @pytest.mark.parametrize(
        [
            "user_id",
            "exp_attrs",
        ],
        [
            (
                1,
                {
                    "name": "NAME1",
                    "email": "name1@example.com",
                    "is_admin": True,
                    "is_confirmed": True,
                },
            ),
            (
                2,
                {
                    "name": "NAME2",
                    "email": "name2@example.com",
                    "is_confirmed": True,
                    "is_admin": False,
                },
            ),
        ],
    )
    def test_attrs(self, user_id, exp_attrs, db_session):
        user = db_session.get(models.User, user_id)
        for name, value in exp_attrs.items():
            assert getattr(user, name) == value

    @pytest.mark.parametrize(
        [
            "user_id",
            "rel_import_ids",
            "rel_study_ids",
            "rel_screening_ids",
            "rel_review_ids",
            "rel_owned_review_ids",
            "collaborator_ids",
        ],
        [
            (
                1,
                [],
                [],
                [],
                [1],
                [1],
                [2, 3],
            ),
            (
                2,
                [1, 2],
                [1, 2, 3],
                [1, 2, 3, 4, 6, 8],
                [1, 2],
                [1, 2],
                [1, 3],
            ),
        ],
    )
    def test_relationships(
        self,
        user_id,
        rel_import_ids,
        rel_study_ids,
        rel_screening_ids,
        rel_review_ids,
        rel_owned_review_ids,
        collaborator_ids,
        db_session,
    ):
        user = db_session.get(models.User, user_id)
        assert [
            i.id for i in db_session.execute(user.imports.select()).scalars()
        ] == rel_import_ids
        assert [
            s.id for s in db_session.execute(user.studies.select()).scalars()
        ] == rel_study_ids
        assert [
            s.id for s in db_session.execute(user.screenings.select()).scalars()
        ] == rel_screening_ids
        assert [r.id for r in user.reviews] == rel_review_ids
        assert [r.id for r in user.owned_reviews] == rel_owned_review_ids
        assert [u.id for u in user.collaborators] == collaborator_ids


class TestReview:
    @pytest.mark.parametrize(
        [
            "review_id",
            "exp_attrs",
        ],
        [
            (
                1,
                {
                    "name": "NAME1",
                    "description": "DESCRIPTION1",
                    "status": "active",
                    "citation_reviewer_num_pcts": [{"num": 1, "pct": 100}],
                    "fulltext_reviewer_num_pcts": [{"num": 1, "pct": 100}],
                },
            ),
            (
                2,
                {
                    "name": "NAME2",
                    "description": "DESCRIPTION2",
                    "status": "active",
                    "citation_reviewer_num_pcts": [
                        {"num": 1, "pct": 75},
                        {"num": 2, "pct": 25},
                    ],
                    "fulltext_reviewer_num_pcts": [{"num": 2, "pct": 100}],
                },
            ),
        ],
    )
    def test_attrs(self, review_id, exp_attrs, db_session):
        review = db_session.get(models.Review, review_id)
        for name, value in exp_attrs.items():
            assert getattr(review, name) == value

    @pytest.mark.parametrize(
        [
            "review_id",
            "rel_user_ids",
            "rel_import_ids",
            "rel_study_ids",
            "rel_screening_ids",
            "rel_dedupe_ids",
            "rel_data_extraction_ids",
            "rel_owner_ids",
        ],
        [
            (
                1,
                [1, 2, 3],
                [1, 2],
                [1, 2, 3],
                [1, 2, 3, 6, 7, 8],
                [],
                [1],
                [1, 2],
            ),
            (
                2,
                [2, 3],
                [3],
                [4],
                [4, 5],
                [],
                [],
                [2],
            ),
        ],
    )
    def test_relationships(
        self,
        review_id,
        rel_user_ids,
        rel_import_ids,
        rel_study_ids,
        rel_screening_ids,
        rel_dedupe_ids,
        rel_data_extraction_ids,
        rel_owner_ids,
        db_session,
    ):
        review = db_session.get(models.Review, review_id)
        assert [obj.id for obj in review.users] == rel_user_ids
        assert [
            obj.id for obj in db_session.execute(review.imports.select()).scalars()
        ] == rel_import_ids
        assert [
            obj.id for obj in db_session.execute(review.studies.select()).scalars()
        ] == rel_study_ids
        assert [
            obj.id for obj in db_session.execute(review.screenings.select()).scalars()
        ] == rel_screening_ids
        assert [
            obj.id for obj in db_session.execute(review.dedupes.select()).scalars()
        ] == rel_dedupe_ids
        assert [
            obj.id
            for obj in db_session.execute(review.data_extractions.select()).scalars()
        ] == rel_data_extraction_ids
        assert [obj.id for obj in review.owners] == rel_owner_ids

    @pytest.mark.parametrize(
        ["review_id", "stage", "statuses", "exp_result"],
        [
            (1, "citation", ["included", "excluded"], {"included": 2, "excluded": 1}),
            (1, "fulltext", ["included", "excluded"], {"included": 1, "excluded": 1}),
            (2, "citation", ["included", "excluded"], {"included": 1, "excluded": 0}),
            (
                2,
                "fulltext",
                ["not_screened", "included"],
                {"not_screened": 1, "included": 0},
            ),
        ],
    )
    def test_num_studies_by_status(
        self, review_id, stage, statuses, exp_result, db_session
    ):
        review = db_session.get(models.Review, review_id)
        if stage == "citation":
            assert review.num_citations_by_status(statuses) == exp_result
        elif stage == "fulltext":
            assert review.num_fulltexts_by_status(statuses) == exp_result


class TestStudy:
    @pytest.mark.parametrize(
        [
            "study_id",
            "exp_attrs",
        ],
        [
            (
                1,
                {
                    "tags": ["TAG1"],
                    "fulltext": {
                        "filename": "1.pdf",
                        "original_filename": "example-journal-short.pdf",
                        "text_content": "This is an example text in English.",
                    },
                    "num_citation_reviewers": 1,
                    "num_fulltext_reviewers": 1,
                },
            ),
            (
                2,
                {
                    "tags": ["TAG3", "TAG2", "TAG1"],
                    "fulltext": {
                        "filename": "2.pdf",
                        "original_filename": "example-journal.pdf",
                        "text_content": "This is another example text in English.",
                    },
                },
            ),
        ],
    )
    def test_attrs(self, study_id, exp_attrs, db_session):
        study = db_session.get(models.Study, study_id)
        for name, value in exp_attrs.items():
            assert getattr(study, name) == value

    @pytest.mark.parametrize(
        [
            "study_id",
            "rel_user_id",
            "rel_review_id",
            "rel_data_source_id",
            "rel_dedupe_id",
            "rel_data_extraction_id",
            "rel_screening_ids",
        ],
        [
            (
                1,
                2,
                1,
                1,
                None,
                1,
                [1, 6, 7],
            ),
        ],
    )
    def test_relationships(
        self,
        study_id,
        rel_user_id,
        rel_review_id,
        rel_data_source_id,
        rel_dedupe_id,
        rel_data_extraction_id,
        rel_screening_ids,
        db_session,
    ):
        study = db_session.get(models.Study, study_id)
        assert isinstance(study.user, models.User) and study.user.id == rel_user_id
        assert (
            isinstance(study.review, models.Review) and study.review.id == rel_review_id
        )
        assert (
            isinstance(study.data_source, models.DataSource)
            and study.data_source.id == rel_data_source_id
        )
        if rel_dedupe_id is None:
            assert study.dedupe is None
        else:
            assert (
                isinstance(study.dedupe, models.Dedupe)
                and study.dedupe.id == rel_dedupe_id
            )
        if rel_data_extraction_id is None:
            assert study.data_extraction is None
        else:
            assert (
                isinstance(study.data_extraction, models.DataExtraction)
                and study.data_extraction.id == rel_data_extraction_id
            )
        assert [
            obj.id for obj in db_session.execute(study.screenings.select()).scalars()
        ] == rel_screening_ids

    @pytest.mark.parametrize(
        ["study_id", "exp_result_py", "exp_result_expr"],
        [
            (
                1,
                "TITLE1\n\nABSTRACT1\n\nKEYWORD1_1, KEYWORD1_2",
                'TITLE1\n\nABSTRACT1\n\n"KEYWORD1_1", "KEYWORD1_2"',
            ),
            (
                2,
                "TITLE2\n\nABSTRACT2\n\nKEYWORD2",
                'TITLE2\n\nABSTRACT2\n\n"KEYWORD2"',
            ),
        ],
    )
    def test_citation_text_content(
        self, study_id, exp_result_py, exp_result_expr, db_session
    ):
        study = db_session.get(models.Study, study_id)
        assert study.citation_text_content == exp_result_py

        result_expr = (
            db_session.execute(
                sa.select(models.Study.citation_text_content).filter_by(id=study_id)
            )
            .scalars()
            .one()
        )
        assert result_expr == exp_result_expr

    @pytest.mark.parametrize(
        ["study_id", "stage", "exp_result"],
        [
            (1, "citation", []),
            (1, "fulltext", []),
            (3, "citation", ["REASON1", "REASON2"]),
            (2, "fulltext", ["REASON1", "REASON2"]),
        ],
    )
    def test_exclude_reasons(self, study_id, stage, exp_result, db_session):
        study = db_session.get(models.Study, study_id)
        if stage == "citation":
            assert study.citation_exclude_reasons == exp_result
        elif stage == "fulltext":
            assert study.fulltext_exclude_reasons == exp_result
