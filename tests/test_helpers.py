"""Tests for `helpers.APIClient`."""


class TestAPIClient:
    def test_admin_get(self, api):
        resp = api.get("health.health")
        assert resp.status_code == 200
        assert resp.json == {"message": "OK"}

    def test_admin_get_with_params(self, api):
        resp = api.get("reviews.review", id=1)
        assert resp.status_code == 200
        assert resp.json["id"] == 1

    def test_as_user_get_own_profile(self, api):
        resp = api.as_user(1).get("users.user", id=1)
        assert resp.status_code == 200
        assert resp.json["id"] == 1

    def test_as_user_gets_403_for_others(self, api):
        resp = api.as_user(4).get("users.user", id=1)
        assert resp.status_code == 403

    def test_admin_put(self, api):
        resp = api.put(
            "reviews.review",
            id=1,
            json={"name": "TEST_RENAME"},
        )
        assert resp.status_code == 200
        assert resp.json["name"] == "TEST_RENAME"

    def test_as_user_put(self, api):
        resp = api.as_user(1).put(
            "reviews.review",
            id=1,
            json={"name": "TEST_RENAME2"},
        )
        assert resp.status_code == 200
        assert resp.json["name"] == "TEST_RENAME2"

    def test_admin_delete(self, api):
        resp = api.delete("reviews.review", id=1)
        # Only owners can delete; admin id 1 is owner of review 1
        assert resp.status_code == 204

    def test_as_user_delete_own_review(self, api):
        # User 2 owns review 2
        resp = api.as_user(2).delete("reviews.review", id=2)
        assert resp.status_code == 204

    def test_user_mode_is_sticky(self, api):
        """as_user() persists across multiple requests on the same instance."""
        api.as_user(4)
        resp1 = api.get("users.user", id=4)  # self — ok
        assert resp1.status_code == 200
        resp2 = api.get("users.user", id=1)  # still user 4 — should 403
        assert resp2.status_code == 403
