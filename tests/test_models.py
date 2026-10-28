"""Tests for `colandr/models.py`.

Model attribute, relationship, derived-property, and event-listener tests,

Notes:

- The ORM layer's validation is limited to database non-null/foreign-key/unique constraints.
- Model event listeners are part of the contract and thus tested here, not directly
  in factory/API tests, which only have to deal with their side-effects.
- `update_study_status` writes study status with a Core UPDATE, so a study held
  in the session is stale after any screening insert/update/delete => expire before asserting.
"""

import random

import pytest
import sqlalchemy as sa

from colandr import models, tasks

from . import factories


pytestmark = pytest.mark.usefixtures("db_empty")


def count_rows(session, model) -> int:
    """Count ``model`` rows in the database, bypassing stale session objects."""
    return session.execute(sa.select(sa.func.count()).select_from(model)).scalar_one()


class TestUser:
    def test_attrs(self, db_session):
        user = factories.create_user(
            db_session, name="User", email="user@example.com", is_admin=True
        )
        assert user.name == "User"
        assert user.email == "user@example.com"
        assert user.is_admin is True
        assert user.is_confirmed is True

    def test_relationships(self, db_session):
        owner, member, collaborator = factories.create_users(
            db_session, n=3, names=["Owner", "Member", "Collaborator"]
        )
        review = factories.create_review_with_team(
            db_session, owner=owner, members=[member]
        )
        other_review = factories.create_review_with_team(
            db_session, owner=owner, members=[collaborator]
        )
        study = factories.create_study(db_session, review=review, user=owner)
        screening = factories.create_screening(db_session, study=study, user=owner)

        assert [r.id for r in owner.reviews] == [review.id, other_review.id]
        assert [r.id for r in owner.owned_reviews] == [review.id, other_review.id]
        assert [u.id for u in owner.collaborators] == [member.id, collaborator.id]
        assert [s.id for s in db_session.execute(owner.studies.select()).scalars()] == [
            study.id
        ]
        assert [
            s.id for s in db_session.execute(owner.screenings.select()).scalars()
        ] == [screening.id]
        import_record = factories.create_import(db_session, review, user=owner)
        assert [i.id for i in db_session.execute(owner.imports.select()).scalars()] == [
            import_record.id
        ]


class TestReview:
    def test_attrs(self, db_session):
        review = factories.create_review(
            db_session,
            name="NAME",
            description="DESCRIPTION.",
            citation_reviewer_num_pcts=[{"num": 1, "pct": 75}, {"num": 2, "pct": 25}],
            fulltext_reviewer_num_pcts=[{"num": 2, "pct": 100}],
        )
        assert review.name == "NAME"
        assert review.description == "DESCRIPTION."
        assert review.status == "active"
        assert review.citation_reviewer_num_pcts == [
            {"num": 1, "pct": 75},
            {"num": 2, "pct": 25},
        ]
        assert review.fulltext_reviewer_num_pcts == [{"num": 2, "pct": 100}]

    def test_relationships(self, db_session):
        owner, member = factories.create_users(db_session, n=2)
        review = factories.create_review_with_team(
            db_session, owner=owner, members=[member]
        )
        study = factories.create_study(db_session, review=review, user=owner)
        import_record = factories.create_import(db_session, review, user=owner)

        assert [u.id for u in review.users] == [owner.id, member.id]
        assert [u.id for u in review.owners] == [owner.id]
        assert [
            s.id for s in db_session.execute(review.studies.select()).scalars()
        ] == [study.id]
        assert [
            i.id for i in db_session.execute(review.imports.select()).scalars()
        ] == [import_record.id]
        assert [
            d.id for d in db_session.execute(review.dedupes.select()).scalars()
        ] == []
        assert [
            e.id for e in db_session.execute(review.data_extractions.select()).scalars()
        ] == []

    def test_num_studies_by_status(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        included = factories.create_study(db_session, review=review, user=user)
        excluded = factories.create_study(db_session, review=review, user=user)
        unscreened = factories.create_study(db_session, review=review, user=user)
        factories.create_screening(
            db_session, study=included, user=user, status="included"
        )
        factories.create_screening(
            db_session, study=excluded, user=user, status="excluded"
        )

        assert review.num_citations_by_status(["included", "excluded"]) == {
            "included": 1,
            "excluded": 1,
        }
        assert review.num_fulltexts_by_status(["not_screened"]) == {"not_screened": 3}


class TestReviewUserAssoc:
    def test_init_defaults_and_repr(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        assoc = models.ReviewUserAssoc(review, user)
        db_session.add(assoc)
        db_session.flush()

        assert assoc.review_id == review.id and assoc.user_id == user.id
        assert assoc.user_role == "member"  # filled in by server default
        assert repr(assoc) == (
            f"<ReviewUserAssoc(review_id={review.id}, user_id={user.id})>"
        )

    @pytest.mark.parametrize("user_role", ["owner", "member", "OWNER", "typo"])
    def test_user_role_is_unconstrained(self, db_session, user_role):
        # FIXME: any string is accepted; only "owner" is load-bearing for authz
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        assoc = models.ReviewUserAssoc(review, user, user_role=user_role)
        db_session.add(assoc)
        db_session.flush()

        assert assoc.user_role == user_role

    def test_composite_primary_key_is_unique(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        factories.add_review_user(db_session, review, user, role="owner")

        db_session.add(models.ReviewUserAssoc(review, user))
        with pytest.raises(sa.exc.IntegrityError):
            db_session.flush()

    @pytest.mark.parametrize("parent", ["review", "user"])
    def test_delete_parent_cascades(self, db_session, parent):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        factories.add_review_user(db_session, review, user)

        db_session.delete(review if parent == "review" else user)
        db_session.flush()

        assert count_rows(db_session, models.ReviewUserAssoc) == 0


class TestReviewPlan:
    def test_created_for_each_review_with_defaults(self, db_session):
        review = factories.create_review(db_session)
        plan = db_session.get(models.ReviewPlan, review.id)

        assert plan is not None
        assert plan.id == review.id
        assert plan.objective is None
        assert plan.research_questions == []
        assert plan.pico == {}
        assert plan.suggested_keyterms == {}
        # FIXME: keyterms annotated as lists but defaulting to a JSONB object
        assert plan.keyterms == {}
        assert plan.selection_criteria == {}
        assert plan.data_extraction_form == {}
        assert plan.boolean_search_query == ""

    def test_boolean_search_query(self, db_session):
        review = factories.create_review(db_session)
        plan = factories.update_review_plan(
            db_session,
            review,
            keyterms=[
                {"term": "TERM1", "group": "GROUP2", "synonyms": []},
                {"term": "TERM2", "group": "GROUP1", "synonyms": ["SYN2"]},
            ],
        )

        assert plan.boolean_search_query == '("TERM2" OR "SYN2")\nAND\n"TERM1"'

    def test_relationships_and_cascade(self, db_session):
        review = factories.create_review(db_session)
        plan = db_session.get(models.ReviewPlan, review.id)
        assert plan.review is review

        db_session.delete(review)
        db_session.flush()

        assert count_rows(db_session, models.ReviewPlan) == 0


class TestDataSource:
    def test_attrs(self, db_session):
        source = factories.create_data_source(
            db_session,
            source_type="database",
            source_name="PubMed",
            source_url="https://pubmed.ncbi.nlm.nih.gov",
        )

        assert source.source_type == "database"
        assert source.source_name == "PubMed"
        assert source.source_url == "https://pubmed.ncbi.nlm.nih.gov"
        assert repr(source) == f"<DataSource(id={source.id})>"

    @pytest.mark.parametrize(
        ["source_name", "exp_label"],
        [("PubMed", "database: PubMed"), (None, "database"), ("", "database")],
    )
    def test_source_type_and_name(self, source_name, exp_label):
        source = models.DataSource(source_type="database", source_name=source_name)
        assert source.source_type_and_name == exp_label

    def test_unique_type_name_url(self, db_session):
        """NULL urls compare equal here: the constraint is NULLS NOT DISTINCT."""
        source = factories.create_data_source(db_session, source_name="PubMed")

        db_session.add(
            models.DataSource(source_type=source.source_type, source_name="PubMed")
        )
        with pytest.raises(sa.exc.IntegrityError):
            db_session.flush()

    def test_delete_nulls_references(self, db_session):
        source = factories.create_data_source(db_session)
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(
            db_session, review=review, user=user, data_source=source
        )
        import_record = factories.create_import(
            db_session, review, user=user, data_source=source
        )

        db_session.delete(source)
        db_session.flush()
        db_session.expire_all()

        assert db_session.get(models.Study, study.id).data_source_id is None
        assert db_session.get(models.Import, import_record.id).data_source_id is None


class TestImport:
    def test_server_defaults(self, db_session):
        review = factories.create_review(db_session)
        record = models.Import(
            review_id=review.id, record_type="citation", num_records=3
        )
        db_session.add(record)
        db_session.flush()

        assert record.num_records == 3
        assert record.status == "not_screened"
        assert record.user_id is None
        assert record.data_source_id is None

    def test_relationships(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        source = factories.create_data_source(db_session)
        record = factories.create_import(
            db_session, review, user=user, data_source=source, num_records=5
        )

        assert record.review is review
        assert record.user is user
        assert record.data_source is source
        assert record.num_records == 5
        assert repr(record) == f"<Import(id={record.id}, review_id={review.id})>"

    def test_delete_user_and_source_null_references(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        source = factories.create_data_source(db_session)
        record = factories.create_import(
            db_session, review, user=user, data_source=source
        )

        db_session.delete(user)
        db_session.delete(source)
        db_session.flush()
        db_session.refresh(record)

        assert record.user_id is None
        assert record.data_source_id is None
        assert count_rows(db_session, models.Import) == 1

    def test_delete_review_cascades(self, db_session):
        review = factories.create_review(db_session)
        factories.create_import(db_session, review)

        db_session.delete(review)
        db_session.flush()

        assert count_rows(db_session, models.Import) == 0


class TestStudy:
    def test_attrs(self, db_session):
        user = factories.create_user(db_session)
        review = factories.create_review(db_session)
        data_source = factories.create_data_source(db_session, source_name="PubMed")
        study = factories.create_study(
            db_session,
            review=review,
            user=user,
            data_source=data_source,
            tags=["TAG1"],
            fulltext={"filename": "1.pdf", "text_content": "Full text."},
        )
        assert study.tags == ["TAG1"]
        assert study.fulltext["filename"] == "1.pdf"
        assert study.num_citation_reviewers == 1
        assert study.num_fulltext_reviewers == 1

    def test_relationships(self, db_session):
        user = factories.create_user(db_session)
        review = factories.create_review(db_session)
        data_source = factories.create_data_source(db_session)
        study = factories.create_study(
            db_session, review=review, user=user, data_source=data_source
        )
        screening = factories.create_screening(db_session, study=study, user=user)

        assert study.user is user
        assert study.review is review
        assert study.data_source is data_source
        assert study.dedupe is None
        assert study.data_extraction is None
        assert [
            s.id for s in db_session.execute(study.screenings.select()).scalars()
        ] == [screening.id]

    def test_citation_text_content(self, db_session):
        review = factories.create_review(db_session)
        study = factories.create_study(
            db_session,
            review=review,
            citation={
                "type_of_reference": "journal",
                "title": "TITLE",
                "abstract": "ABSTRACT",
                "keywords": ["KW1", "KW2"],
            },
        )
        assert study.citation_text_content == "TITLE\n\nABSTRACT\n\nKW1, KW2"

        result = (
            db_session.execute(
                sa.select(models.Study.citation_text_content).filter_by(id=study.id)
            )
            .scalars()
            .one()
        )
        assert result == 'TITLE\n\nABSTRACT\n\n"KW1", "KW2"'

    def test_exclude_reasons(self, db_session):
        user = factories.create_user(db_session)
        review = factories.create_review(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        factories.create_screening(
            db_session,
            study=study,
            user=user,
            status="excluded",
            exclude_reasons=["REASON2", "REASON1"],
        )
        assert study.citation_exclude_reasons == ["REASON1", "REASON2"]

    def test_fulltext_exclude_reasons(self, db_session):
        user = factories.create_user(db_session)
        review = factories.create_review(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        factories.create_screening(
            db_session, study=study, user=user, status="included"
        )
        factories.create_screening(
            db_session,
            study=study,
            user=user,
            stage="fulltext",
            status="excluded",
            exclude_reasons=["REASON2", "REASON1"],
        )
        assert study.fulltext_exclude_reasons == ["REASON1", "REASON2"]


class TestScreening:
    def test_attrs(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        screening = models.Screening(
            user_id=user.id,
            review_id=review.id,
            study_id=study.id,
            stage="citation",
            status="included",
        )
        db_session.add(screening)
        db_session.flush()

        assert screening.exclude_reasons is None
        assert screening.user is user
        assert screening.review is review
        assert screening.study is study
        assert repr(screening) == (
            f"<Screening(id={screening.id}, study_id={study.id}, stage='citation')>"
        )

    @pytest.mark.parametrize("missing", ["stage", "status", "review_id", "study_id"])
    def test_required_columns(self, db_session, missing):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        kwargs = {
            "user_id": user.id,
            "review_id": review.id,
            "study_id": study.id,
            "stage": "citation",
            "status": "included",
        }
        del kwargs[missing]

        db_session.add(models.Screening(**kwargs))
        with pytest.raises(sa.exc.IntegrityError):
            db_session.flush()

    def test_unique_per_user_study_stage(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        factories.create_screening(
            db_session, study=study, user=user, status="included"
        )

        db_session.add(
            models.Screening(
                user_id=user.id,
                review_id=review.id,
                study_id=study.id,
                stage="citation",
                status="excluded",
            )
        )
        with pytest.raises(sa.exc.IntegrityError):
            db_session.flush()

    def test_delete_user_nulls_user_id(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        screening = factories.create_screening(db_session, study=study, user=user)

        db_session.delete(user)
        db_session.flush()
        db_session.refresh(screening)

        assert screening.user_id is None
        assert screening.status == "included"  # the decision outlives the reviewer!

    @pytest.mark.parametrize("parent", ["review", "study"])
    def test_delete_parent_cascades(self, db_session, parent):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review, user=user)
        factories.create_screening(db_session, study=study, user=user)

        db_session.delete(review if parent == "review" else study)
        db_session.flush()

        assert count_rows(db_session, models.Screening) == 0


class TestDedupe:
    def test_attrs_and_relationships(self, db_session):
        review = factories.create_review(db_session)
        study, duplicate = factories.create_studies(db_session, 2, review=review)
        dedupe = models.Dedupe(
            study_id=study.id,
            review_id=review.id,
            duplicate_of=duplicate.id,
            duplicate_score=0.75,
        )
        db_session.add(dedupe)
        db_session.flush()

        assert dedupe.study is study
        assert dedupe.review is review
        assert dedupe.duplicate_of == duplicate.id
        assert dedupe.duplicate_score == 0.75
        assert repr(dedupe) == f"<Dedupe(id={dedupe.id}, study_id={study.id})>"

    def test_one_per_study(self, db_session):
        review = factories.create_review(db_session)
        study, duplicate = factories.create_studies(db_session, 2, review=review)
        db_session.add(models.Dedupe(study_id=study.id, review_id=review.id))
        db_session.flush()

        db_session.add(
            models.Dedupe(
                study_id=study.id, review_id=review.id, duplicate_of=duplicate.id
            )
        )
        with pytest.raises(sa.exc.IntegrityError):
            db_session.flush()

    @pytest.mark.parametrize("parent", ["study", "review"])
    def test_delete_parent_cascades(self, db_session, parent):
        review = factories.create_review(db_session)
        study, duplicate = factories.create_studies(db_session, 2, review=review)
        db_session.add(
            models.Dedupe(
                study_id=study.id, review_id=review.id, duplicate_of=duplicate.id
            )
        )
        db_session.flush()

        db_session.delete(study if parent == "study" else review)
        db_session.flush()

        assert count_rows(db_session, models.Dedupe) == 0


class TestDataExtraction:
    def test_defaults_and_relationships(self, db_session):
        review = factories.create_review(db_session)
        study = factories.create_study(db_session, review=review)
        extraction = models.DataExtraction(study_id=study.id, review_id=review.id)
        db_session.add(extraction)
        db_session.flush()

        # FIXME: annotated as a list but defaults to a JSONB object
        assert extraction.extracted_items == {}
        assert extraction.study is study
        assert extraction.review is review
        assert extraction.created_at is not None
        assert repr(extraction) == (
            f"<DataExtraction(id={extraction.id}, study_id={study.id})>"
        )

    @pytest.mark.parametrize(
        "extracted_items",
        [[], [{"label": "LABEL", "value": "VALUE"}]],
    )
    def test_extracted_items_roundtrip(self, db_session, extracted_items):
        review = factories.create_review(db_session)
        study = factories.create_study(db_session, review=review)
        extraction = models.DataExtraction(
            study_id=study.id, review_id=review.id, extracted_items=extracted_items
        )
        db_session.add(extraction)
        db_session.flush()

        db_session.expire(extraction)
        assert extraction.extracted_items == extracted_items

    def test_one_per_study(self, db_session):
        review = factories.create_review(db_session)
        study = factories.create_study(db_session, review=review)
        db_session.add(models.DataExtraction(study_id=study.id, review_id=review.id))
        db_session.flush()

        db_session.add(models.DataExtraction(study_id=study.id, review_id=review.id))
        with pytest.raises(sa.exc.IntegrityError):
            db_session.flush()

    @pytest.mark.parametrize("parent", ["study", "review"])
    def test_delete_parent_cascades(self, db_session, parent):
        review = factories.create_review(db_session)
        study = factories.create_study(db_session, review=review)
        db_session.add(models.DataExtraction(study_id=study.id, review_id=review.id))
        db_session.flush()

        db_session.delete(study if parent == "study" else review)
        db_session.flush()

        assert count_rows(db_session, models.DataExtraction) == 0


## EVENT LISTENERS! ##


class _TaskRecorder:
    """Stands in for a Celery task: records the args passed to ``apply_async``."""

    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def apply_async(self, args=None, **kwargs):
        self.calls.append((self.name, list(args)))


class TestScreeningEvents:
    @pytest.mark.parametrize(
        ["num_reviewers", "statuses", "exp_status"],
        [
            (1, ["included"], "included"),
            (1, ["excluded"], "excluded"),
            (2, ["included"], "screened_once"),
            (2, ["included", "included"], "included"),
            (2, ["included", "excluded"], "conflict"),
            (3, ["excluded", "excluded"], "screened_twice"),
            (3, ["excluded", "excluded", "excluded"], "excluded"),
        ],
    )
    def test_insert_recomputes_study_status(
        self, db_session, num_reviewers, statuses, exp_status
    ):
        review = factories.create_review(db_session)
        users = factories.create_users(db_session, n=num_reviewers)
        study = factories.create_study(
            db_session, review=review, num_citation_reviewers=num_reviewers
        )

        for user, status in zip(users, statuses, strict=False):
            factories.create_screening(
                db_session, study=study, user=user, status=status
            )

        assert study.citation_status == exp_status

    def test_update_recomputes_study_status(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review)
        screening = factories.create_screening(
            db_session, study=study, user=user, status="included"
        )
        assert study.citation_status == "included"

        screening.status = "excluded"
        db_session.flush()
        db_session.expire(study)

        assert study.citation_status == "excluded"

    def test_delete_recomputes_study_status(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(
            db_session, review=review, num_citation_reviewers=2
        )
        screening = factories.create_screening(
            db_session, study=study, user=user, status="included"
        )
        assert study.citation_status == "screened_once"

        db_session.delete(screening)
        db_session.flush()
        db_session.expire(study)

        assert study.citation_status == "not_screened"

    def test_fulltext_status_creates_and_deletes_data_extraction(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review)
        factories.create_screening(
            db_session, study=study, user=user, status="included"
        )
        fulltext = factories.create_screening(
            db_session, study=study, user=user, stage="fulltext", status="included"
        )
        db_session.expire(study)

        assert study.fulltext_status == "included"
        (extraction,) = db_session.execute(sa.select(models.DataExtraction)).scalars()
        assert extraction.study_id == study.id
        assert extraction.review_id == review.id

        fulltext.status = "excluded"
        db_session.flush()
        db_session.expire(study)

        assert study.fulltext_status == "excluded"
        assert count_rows(db_session, models.DataExtraction) == 0

    def test_citation_recompute_deletes_fulltext_screenings(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review=review)
        citation = factories.create_screening(
            db_session, study=study, user=user, status="included"
        )
        factories.create_screening(
            db_session, study=study, user=user, stage="fulltext", status="included"
        )

        citation.status = "excluded"
        db_session.flush()
        db_session.expire(study)

        assert [
            s.stage for s in db_session.execute(study.screenings.select()).scalars()
        ] == ["citation"]
        assert study.citation_status == "excluded"
        # FIXME: the listener's Core DELETE fires no events, so the fulltext status
        # goes stale and the data extraction row is orphaned; recompute both stages
        # and delete the extraction explicitly
        assert study.fulltext_status == "included"
        assert count_rows(db_session, models.DataExtraction) == 1

    def test_dispatches_keyterms_suggestion_at_50_screened(
        self, db_session, monkeypatch
    ):
        calls = []
        # the listener imports `colandr.tasks` lazily, so patch the module attributes
        monkeypatch.setattr(
            tasks, "suggest_keyterms", _TaskRecorder("suggest_keyterms", calls)
        )
        monkeypatch.setattr(
            tasks,
            "train_study_ranker_model",
            _TaskRecorder("train_study_ranker_model", calls),
        )
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        studies = factories.create_studies(db_session, 50, review=review)

        for i, study in enumerate(studies):
            status = "included" if i < 25 else "excluded"
            factories.create_screening(
                db_session, study=study, user=user, status=status
            )

        assert calls == [("suggest_keyterms", [review.id, 25])]

    def test_dispatches_ranker_training_at_100_screened(self, db_session, monkeypatch):
        calls = []
        monkeypatch.setattr(
            tasks, "suggest_keyterms", _TaskRecorder("suggest_keyterms", calls)
        )
        monkeypatch.setattr(
            tasks,
            "train_study_ranker_model",
            _TaskRecorder("train_study_ranker_model", calls),
        )
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        studies = factories.create_studies(db_session, 100, review=review)

        for study in studies:
            factories.create_screening(
                db_session, study=study, user=user, status="included"
            )

        assert calls == [("train_study_ranker_model", [review.id])]


class TestReviewEvents:
    def test_update_assigns_num_reviewers_to_unscreened_studies(self, db_session):
        review = factories.create_review(
            db_session, citation_reviewer_num_pcts=[{"num": 3, "pct": 100}]
        )
        studies = factories.create_studies(db_session, 3, review=review)

        review.citation_reviewer_num_pcts = [{"num": 2, "pct": 100}]
        db_session.flush()

        for study in studies:
            db_session.refresh(study)
            assert study.num_citation_reviewers == 2

    def test_update_leaves_screened_studies_alone(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        screened = factories.create_study(db_session, review=review)
        unscreened = factories.create_study(db_session, review=review)
        factories.create_screening(
            db_session, study=screened, user=user, status="included"
        )

        review.citation_reviewer_num_pcts = [{"num": 3, "pct": 100}]
        db_session.flush()
        db_session.refresh(screened)
        db_session.refresh(unscreened)

        assert screened.num_citation_reviewers == 1
        assert unscreened.num_citation_reviewers == 3

    def test_update_uses_configured_weights(self, db_session, monkeypatch):
        review = factories.create_review(
            db_session,
            citation_reviewer_num_pcts=[{"num": 1, "pct": 75}, {"num": 2, "pct": 25}],
        )
        studies = factories.create_studies(db_session, 4, review=review)
        calls = []

        def fake_choices(population, weights=None, k=1):
            calls.append((list(population), list(weights), k))
            return [2] * k

        monkeypatch.setattr(random, "choices", fake_choices)
        review.name = "RENAMED"  # any review update runs the listener
        db_session.flush()

        assert calls == [([1, 2], [75, 25], 4), ([1], [100], 4)]
        for study in studies:
            db_session.refresh(study)
            assert study.num_citation_reviewers == 2

    def test_update_with_no_studies_is_noop(self, db_session):
        review = factories.create_review(db_session)

        review.name = "RENAMED"
        db_session.flush()

        assert count_rows(db_session, models.Study) == 0


class TestModelToDict:
    def test_all_columns_by_default(self, db_session):
        user = factories.create_user(db_session, name="User", email="user@example.com")

        data = models.model_to_dict(user)

        # FIXME: the default field set includes private password column
        # it's safe only because callers serialize through schemas that omit it...
        assert set(data) == {
            "id",
            "created_at",
            "updated_at",
            "name",
            "email",
            "_password",
            "is_confirmed",
            "is_admin",
        }
        assert data["name"] == "User"
        assert data["email"] == "user@example.com"

    def test_fields_subset(self, db_session):
        user = factories.create_user(db_session, name="User")

        assert models.model_to_dict(user, ["id", "name"]) == {
            "id": user.id,
            "name": "User",
        }

    def test_include_hybrid(self, db_session):
        review = factories.create_review(db_session)
        plan = factories.update_review_plan(db_session, review, objective="OBJECTIVE")

        data = models.model_to_dict(plan, include_hybrid=True)

        assert data["objective"] == "OBJECTIVE"
        assert data["boolean_search_query"] == ""
        assert "id" in data

    def test_include_hybrid_ignored_when_fields_given(self, db_session):
        review = factories.create_review(db_session)
        plan = db_session.get(models.ReviewPlan, review.id)

        data = models.model_to_dict(plan, fields=["id"], include_hybrid=True)

        assert data == {"id": review.id}

    def test_unknown_field_raises(self, db_session):
        user = factories.create_user(db_session)

        with pytest.raises(AttributeError):
            models.model_to_dict(user, ["not_a_field"])
