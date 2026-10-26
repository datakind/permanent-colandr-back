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
