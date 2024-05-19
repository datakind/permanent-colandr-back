import pytest

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
