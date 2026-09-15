"""Self-tests for the test factories: determinism, invariants, listener side effects."""

import pytest
import sqlalchemy as sa

from colandr import models
from tests import factories


pytestmark = pytest.mark.usefixtures("db_empty")


def test_create_user_defaults(db_session):
    user = factories.create_user(db_session)
    assert user.id is not None
    assert user.is_admin is False
    assert user.is_confirmed is True
    assert user.check_password("anything") is False  # unusable sentinel


def test_create_user_unique_emails(db_session):
    user1 = factories.create_user(db_session)
    user2 = factories.create_user(db_session)
    assert user1.email != user2.email


def test_create_user_hashes_password_when_given(db_session):
    user = factories.create_user(db_session, password="secret")
    assert user.check_password("secret") is True


def test_create_review_auto_creates_empty_plan(db_session):
    review = factories.create_review(db_session)
    plan = db_session.get(models.ReviewPlan, review.id)
    assert plan is not None
    assert plan.objective is None


def test_create_review_defaults_deterministic_reviewer_pcts(db_session):
    review = factories.create_review(db_session)
    assert review.citation_reviewer_num_pcts == [{"num": 1, "pct": 100}]
    assert review.fulltext_reviewer_num_pcts == [{"num": 1, "pct": 100}]


def test_create_screening_updates_study_status(db_session):
    # passes because the factory expires the study after the listener's Core UPDATE
    review = factories.create_review(db_session)
    user = factories.create_user(db_session)
    study = factories.create_study(db_session, review, user=user)
    assert study.citation_status == "not_screened"
    factories.create_screening(db_session, study, user=user, status="included")
    assert study.citation_status == "included"


def test_create_screening_rejects_fulltext_before_citation_inclusion(db_session):
    """A fulltext row on a citation-excluded study is incoherent, and the
    listener never cleans it up, so the factory refuses to build the state."""
    review = factories.create_review(db_session)
    user = factories.create_user(db_session)
    study = factories.create_study(db_session, review, user=user)
    factories.create_screening(db_session, study, user=user, status="excluded")
    with pytest.raises(ValueError, match="citation_status is 'excluded'"):
        factories.create_screening(
            db_session, study, user=user, stage="fulltext", status="included"
        )


def test_later_citation_exclusion_deletes_existing_fulltext_screening(db_session):
    """The listener's real behavior: the *citation* stage deletes fulltext
    screenings when its recomputed status is anything but ``included``.

    This is the corrected half of revision 1's inverted claim, and it is the
    reason ``create_screening`` must raise rather than rely on the listener.
    """
    review = factories.create_review(db_session)
    user = factories.create_user(db_session)
    study = factories.create_study(db_session, review, user=user)
    factories.create_screening(db_session, study, user=user, status="included")
    factories.create_screening(
        db_session, study, user=user, stage="fulltext", status="included"
    )
    assert study.fulltext_status == "included"  # fresh: the factory expired it
    # retract the citation decision; the listener deletes the fulltext row
    citation = db_session.execute(
        sa.select(models.Screening).filter_by(study_id=study.id, stage="citation")
    ).scalar_one()
    citation.status = "excluded"
    db_session.flush()
    stages = (
        db_session.execute(
            sa.select(models.Screening.stage)
            .filter_by(study_id=study.id)
            .order_by(models.Screening.id)
        )
        .scalars()
        .all()
    )
    assert stages == ["citation"]


def test_update_review_plan_sets_and_flushes(db_session):
    review = factories.create_review(db_session)
    plan = factories.update_review_plan(
        db_session, review, objective="OBJECTIVE", pico={"population": "POPULATION"}
    )
    assert plan.id == review.id
    assert plan.objective == "OBJECTIVE"
    assert db_session.get(models.ReviewPlan, review.id).pico == {
        "population": "POPULATION"
    }


def test_create_screened_review_screens_by_label(db_session):
    owner = factories.create_user(db_session)
    reviewer = factories.create_user(db_session)
    review, studies = factories.create_screened_review(
        db_session,
        owner=owner,
        studies={"s1": {}, "s2": {}},
        screening_reviewer=reviewer,
        decisions=[
            ("s1", None, "citation", "included", None),
            ("s2", None, "citation", "excluded", ["REASON1"]),
        ],
    )
    assert studies["s1"].review_id == review.id
    assert studies["s1"].citation_status == "included"
    assert studies["s2"].citation_status == "excluded"


def test_default_values_are_deterministic(db_session):
    first = factories.create_user(db_session)
    second = factories.create_user(db_session)
    assert first.email != second.email
    assert first.email.endswith("@test.local")
    review = factories.create_review(db_session)
    title1 = factories.create_study(db_session, review).citation["title"]
    title2 = factories.create_study(db_session, review).citation["title"]
    assert title1 != title2
    assert title1.startswith("Test Study ")


def test_store_fulltext_file(app, db_session):
    review = factories.create_review(db_session)
    factories.store_fulltext_file(app, review.id, "1.pdf")
    fs = app.extensions["filesystem"]
    assert fs.exists(f"{app.config['FULLTEXT_UPLOADS_DIR']}/{review.id}/1.pdf")
