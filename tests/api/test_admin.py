"""Tests for the admin API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

GET_REVIEWS_API_ENDPOINT = "admin.get_reviews"
POST_USERS_API_ENDPOINT = "admin.post_users"
NOT_FOUND_ID = 999_999


class TestGetReviewsAPI:
    def test_get(self, api, db_session):
        """Get one or more reviews by id; ids with no match are ignored."""
        review1, review2 = factories.create_reviews(db_session, n=2)
        for review_ids, num_exp in [
            (f"{review1.id}", 1),
            (f"{review1.id},{review2.id}", 2),
            (f"{review1.id},{review2.id},{NOT_FOUND_ID}", 2),
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
