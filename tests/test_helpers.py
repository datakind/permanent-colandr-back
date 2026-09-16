"""Tests for `helpers.APIClient`."""

import pytest

from . import factories


pytestmark = pytest.mark.usefixtures("db_empty")


class TestAPIClient:
    def test_admin_get(self, api):
        resp = api.get("health.health")
        assert resp.status_code == 200
        assert resp.json == {"message": "OK"}

    def test_admin_get_review(self, api, db_session):
        review = factories.create_review(db_session)
        resp = api.get("reviews.review", id=review.id)
        assert resp.status_code == 200
        assert resp.json["id"] == review.id

    def test_as_user_get_own_profile(self, api, db_session):
        user = factories.create_user(db_session)
        resp = api.as_user(user).get("users.user", id=user.id)
        assert resp.status_code == 200
        assert resp.json["id"] == user.id

    def test_as_user_gets_403_for_others(self, api, db_session):
        user = factories.create_user(db_session)
        other = factories.create_user(db_session)
        resp = api.as_user(user).get("users.user", id=other.id)
        assert resp.status_code == 403

    def test_admin_put(self, api, db_session):
        review = factories.create_review(db_session)
        resp = api.put("reviews.review", id=review.id, json={"name": "RENAME"})
        assert resp.status_code == 200
        assert resp.json["name"] == "RENAME"

    def test_as_user_delete_own_review(self, api, db_session):
        owner = factories.create_user(db_session)
        review = factories.create_review_with_team(db_session, owner=owner)
        resp = api.as_user(owner).delete("reviews.review", id=review.id)
        assert resp.status_code == 204

    def test_user_mode_is_sticky(self, api, db_session):
        user = factories.create_user(db_session)
        other_user = factories.create_user(db_session)
        api.as_user(user)
        resp1 = api.get("users.user", id=user.id)  # self => ok
        assert resp1.status_code == 200
        resp2 = api.get("users.user", id=other_user.id)  # still user => 403
        assert resp2.status_code == 403
