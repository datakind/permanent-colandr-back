"""Tests for `colandr/models.py`.

Model attribute, relationship, and derived-property tests, built from factories.
"""

import pytest
import sqlalchemy as sa

from colandr import models

from . import factories


pytestmark = pytest.mark.usefixtures("db_empty")


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
        owner = factories.create_user(db_session, name="Owner")
        member = factories.create_user(db_session, name="Member")
        collaborator = factories.create_user(db_session, name="Collaborator")
        review = factories.create_review_with_team(
            db_session, owner=owner, members=[member]
        )
        other_review = factories.create_review_with_team(
            db_session, owner=owner, members=[collaborator]
        )
        study = factories.create_study(db_session, review, user=owner)
        screening = factories.create_screening(db_session, study, user=owner)

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
        owner = factories.create_user(db_session)
        member = factories.create_user(db_session)
        review = factories.create_review_with_team(
            db_session, owner=owner, members=[member]
        )
        study = factories.create_study(db_session, review, user=owner)
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
        included = factories.create_study(db_session, review, user=user)
        excluded = factories.create_study(db_session, review, user=user)
        unscreened = factories.create_study(db_session, review, user=user)
        factories.create_screening(db_session, included, user=user, status="included")
        factories.create_screening(db_session, excluded, user=user, status="excluded")

        assert review.num_citations_by_status(["included", "excluded"]) == {
            "included": 1,
            "excluded": 1,
        }
        assert review.num_fulltexts_by_status(["not_screened"]) == {"not_screened": 3}


class TestStudy:
    def test_attrs(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        data_source = factories.create_data_source(db_session, source_name="PubMed")
        study = factories.create_study(
            db_session,
            review,
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
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        data_source = factories.create_data_source(db_session)
        study = factories.create_study(
            db_session, review, user=user, data_source=data_source
        )
        screening = factories.create_screening(db_session, study, user=user)

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
            review,
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
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review, user=user)
        factories.create_screening(
            db_session,
            study,
            user=user,
            status="excluded",
            exclude_reasons=["REASON2", "REASON1"],
        )
        assert study.citation_exclude_reasons == ["REASON1", "REASON2"]

    def test_fulltext_exclude_reasons(self, db_session):
        review = factories.create_review(db_session)
        user = factories.create_user(db_session)
        study = factories.create_study(db_session, review, user=user)
        factories.create_screening(db_session, study, user=user, status="included")
        factories.create_screening(
            db_session,
            study,
            user=user,
            stage="fulltext",
            status="excluded",
            exclude_reasons=["REASON2", "REASON1"],
        )
        assert study.fulltext_exclude_reasons == ["REASON1", "REASON2"]
