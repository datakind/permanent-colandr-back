"""Tests for the admin API."""

import pytest
import sqlalchemy as sa

from colandr import models

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

GET_REVIEWS_API_ENDPOINT = "admin.get_reviews"
POST_USERS_API_ENDPOINT = "admin.post_users"
POST_CITATION_SCREENINGS_API_ENDPOINT = "admin.post_citation_screenings"
POST_FULLTEXT_SCREENINGS_API_ENDPOINT = "admin.post_fulltext_screenings"


@pytest.fixture
def screenings_graph(db_session, admin_user):
    """A review with two unscreened studies, and a regular user on its team."""
    member = factories.create_user(db_session)
    review = factories.create_review_with_team(
        db_session, owner=admin_user, members=[member]
    )
    s1, s2 = factories.create_studies(db_session, 2, review=review)
    return {"review": review, "member": member, "s1": s1, "s2": s2}


class TestGetReviewsAPI:
    def test_get(self, api, db_session):
        """Get one or more reviews by id; ids with no match are ignored."""
        review1, review2 = factories.create_reviews(db_session, n=2)
        for review_ids, num_exp in [
            (f"{review1.id}", 1),
            (f"{review1.id},{review2.id}", 2),
            (f"{review1.id},{review2.id},{factories.NOT_FOUND_ID}", 2),
        ]:
            response = api.get(GET_REVIEWS_API_ENDPOINT, review_ids=review_ids)
            assert response.status_code == 200
            assert len(response.json) == num_exp


class TestPostUsersAPI:
    def test_post(self, api):
        """Create a user."""
        data = {"name": "NAMEX", "email": "namex@example.com", "password": "PASSWORDX"}
        response = api.post(POST_USERS_API_ENDPOINT, json=data)
        assert response.status_code == 200
        assert response.json["name"] == data["name"]
        assert response.json["email"] == data["email"]

    @pytest.mark.parametrize(
        "json_data",
        [
            {"name": "NAMEX", "email": "namex@example.com"},
            {"email": "namex@example.com", "password": "PASSWORDX"},
            {"name": "NAMEX", "password": "PASSWORDX"},
        ],
        ids=["no-password", "no-name", "no-email"],
    )
    def test_post_invalid(self, json_data, api):
        """Post an incomplete user record, as an admin."""
        response = api.post(POST_USERS_API_ENDPOINT, json=json_data)
        assert response.status_code == 422

    def test_post_forbidden(self, api, db_session):
        """Post a user record, as a regular user."""
        user = factories.create_user(db_session, is_admin=False)
        data = {"name": "NAMEX", "email": "namex@example.com", "password": "PASSWORDX"}
        response = api.as_user(user).post(POST_USERS_API_ENDPOINT, json=data)
        assert response.status_code == 403


class TestPostCitationScreeningsAPI:
    def test_post(self, screenings_graph, api, db_session, enqueued):
        """Bulk-insert citation screenings; study statuses follow the inserted rows."""
        review = screenings_graph["review"]
        data = [
            {"citation_id": screenings_graph["s1"].id, "status": "included"},
            {
                "citation_id": screenings_graph["s2"].id,
                "status": "excluded",
                "exclude_reasons": ["REASON1"],
            },
        ]
        response = api.post(
            POST_CITATION_SCREENINGS_API_ENDPOINT, json=data, review_id=review.id
        )
        assert response.status_code == 200

        db_session.expire_all()
        assert (
            db_session.get(models.Study, screenings_graph["s1"].id).citation_status
            == "included"
        )
        assert (
            db_session.get(models.Study, screenings_graph["s2"].id).citation_status
            == "excluded"
        )
        # one included + one excluded is below the 25/25 keyterm-suggestion threshold
        assert enqueued["suggest_keyterms"] == []

    def test_post_for_another_user(self, screenings_graph, api, db_session):
        """``user_id`` attributes the screenings to someone other than the caller."""
        review = screenings_graph["review"]
        data = [{"citation_id": screenings_graph["s1"].id, "status": "included"}]
        response = api.post(
            POST_CITATION_SCREENINGS_API_ENDPOINT,
            json=data,
            review_id=review.id,
            user_id=screenings_graph["member"].id,
        )
        assert response.status_code == 200
        screening = db_session.execute(
            sa.select(models.Screening).filter_by(study_id=screenings_graph["s1"].id)
        ).scalar_one()
        assert screening.user_id == screenings_graph["member"].id
        assert screening.stage == "citation"

    @pytest.mark.parametrize(
        "params",
        [{}, {"review_id": 0}],
        ids=["missing-review-id", "review-id-too-small"],
    )
    def test_post_invalid(self, params, api):
        """Reject a bulk insert with a missing or out-of-range review id."""
        data = [{"citation_id": 1, "status": "included"}]
        assert (
            api.post(
                POST_CITATION_SCREENINGS_API_ENDPOINT, json=data, **params
            ).status_code
            == 422
        )

    def test_post_unknown_review(self, screenings_graph, api):
        """Refuse to insert screenings for a review that doesn't exist."""
        data = [{"citation_id": screenings_graph["s1"].id, "status": "included"}]
        response = api.post(
            POST_CITATION_SCREENINGS_API_ENDPOINT,
            json=data,
            review_id=factories.NOT_FOUND_ID,
        )
        assert response.status_code == 404

    def test_post_forbidden(self, screenings_graph, api):
        """Only admins may bulk-insert screenings."""
        data = [{"citation_id": screenings_graph["s1"].id, "status": "included"}]
        response = api.as_user(screenings_graph["member"]).post(
            POST_CITATION_SCREENINGS_API_ENDPOINT,
            json=data,
            review_id=screenings_graph["review"].id,
        )
        assert response.status_code == 403

    def test_post_without_study_id_raises(self, screenings_graph, api):
        """A screening naming neither citation nor study id violates the schema.

        FIXME: the route derives study_id from citation_id/fulltext_id, so a body with
        neither reaches the INSERT with a NULL study_id and raises IntegrityError
        instead of returning a 400 error. Validate the id before inserting!
        """
        data = [{"status": "included"}]
        with pytest.raises(sa.exc.IntegrityError):
            api.post(
                POST_CITATION_SCREENINGS_API_ENDPOINT,
                json=data,
                review_id=screenings_graph["review"].id,
            )


class TestPostFulltextScreeningsAPI:
    def test_post(self, screenings_graph, api, db_session):
        """Bulk-insert fulltext screenings, backfilling extractions for inclusions."""
        review = screenings_graph["review"]
        s1, s2 = screenings_graph["s1"], screenings_graph["s2"]
        data = [
            {"fulltext_id": s1.id, "status": "included"},
            {
                "fulltext_id": s2.id,
                "status": "excluded",
                "exclude_reasons": ["REASON1"],
            },
        ]
        response = api.post(
            POST_FULLTEXT_SCREENINGS_API_ENDPOINT, json=data, review_id=review.id
        )
        assert response.status_code == 200

        db_session.expire_all()
        assert db_session.get(models.Study, s1.id).fulltext_status == "included"
        assert db_session.get(models.Study, s2.id).fulltext_status == "excluded"
        # the route hand-creates the extraction the screening listener would have made
        extractions = (
            db_session.execute(
                sa.select(models.DataExtraction).filter_by(review_id=review.id)
            )
            .scalars()
            .all()
        )
        assert [extraction.study_id for extraction in extractions] == [s1.id]

    def test_post_does_not_duplicate_extractions(
        self, screenings_graph, api, db_session
    ):
        """A study that already has an extraction doesn't get a second one."""
        review = screenings_graph["review"]
        s1 = screenings_graph["s1"]
        # a second reviewer, so the insert doesn't trip the
        # (user, review, study, stage) uniqueness constraint
        for user_id in (None, screenings_graph["member"].id):
            extra = {"user_id": user_id} if user_id is not None else {}
            assert (
                api.post(
                    POST_FULLTEXT_SCREENINGS_API_ENDPOINT,
                    json=[{"fulltext_id": s1.id, "status": "included"}],
                    review_id=review.id,
                    **extra,
                ).status_code
                == 200
            )
        count = db_session.execute(
            sa.select(sa.func.count())
            .select_from(models.DataExtraction)
            .filter_by(study_id=s1.id)
        ).scalar_one()
        assert count == 1

    def test_post_unknown_review(self, screenings_graph, api):
        """Refuse to insert screenings for a review that doesn't exist."""
        data = [{"fulltext_id": screenings_graph["s1"].id, "status": "included"}]
        response = api.post(
            POST_FULLTEXT_SCREENINGS_API_ENDPOINT,
            json=data,
            review_id=factories.NOT_FOUND_ID,
        )
        assert response.status_code == 404

    def test_post_forbidden(self, screenings_graph, api):
        """Only admins may bulk-insert screenings."""
        data = [{"fulltext_id": screenings_graph["s1"].id, "status": "included"}]
        response = api.as_user(screenings_graph["member"]).post(
            POST_FULLTEXT_SCREENINGS_API_ENDPOINT,
            json=data,
            review_id=screenings_graph["review"].id,
        )
        assert response.status_code == 403

    def test_post_without_study_id_raises(self, screenings_graph, api):
        """A screening naming neither fulltext nor study id violates the schema.

        FIXME: same problem as the citation equivalent: INSERT carries a NULL study_id
        and raises IntegrityError instead of returning a 400 error
        """
        data = [{"status": "included"}]
        with pytest.raises(sa.exc.IntegrityError):
            api.post(
                POST_FULLTEXT_SCREENINGS_API_ENDPOINT,
                json=data,
                review_id=screenings_graph["review"].id,
            )
