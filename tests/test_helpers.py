"""Tests for `helpers.APIClient`."""

import pytest

from colandr.api.v1 import authn

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
        user, other_user = factories.create_users(db_session, n=2)
        resp = api.as_user(user).get("users.user", id=other_user.id)
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
        user, other_user = factories.create_users(db_session, n=2)
        api.as_user(user)
        resp1 = api.get("users.user", id=user.id)  # self => ok
        assert resp1.status_code == 200
        resp2 = api.get("users.user", id=other_user.id)  # still user => 403
        assert resp2.status_code == 403

    def test_explicit_headers_replace_the_default_auth(self, api, db_session):
        """Explicit ``headers`` wins over admin mode, and ``{}`` is anonymous."""
        user = factories.create_user(db_session)
        own = api.get(
            "users.user", id=user.id, headers=authn.pack_header_for_user(user)
        )
        assert own.status_code == 200
        assert api.get("users.user", id=user.id, headers={}).status_code == 401


class TestFakeRedis:
    def test_blocklist_round_trip(self, fake_redis):
        """JWT blocklist reads and writes an in-memory store, without actual Redis."""
        assert authn._is_blocklisted("jti-001") is False
        authn._add_to_blocklist("jti-001", ttl_seconds=60)
        assert authn._is_blocklisted("jti-001") is True

    def test_is_empty_at_start(self, fake_redis):
        """Each test starts with an empty blocklist, whatever earlier tests revoked."""
        assert fake_redis.store == {}
