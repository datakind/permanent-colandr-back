"""Tests for the users API."""

import flask
import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

USER_API_ENDPOINT = "users.user"
USERS_API_ENDPOINT = "users.users"
NOT_FOUND_ID = 999_999


def _user_url(client, user_id: int) -> str:
    """Build a user endpoint url, outside of any request context."""
    with client.application.test_request_context():
        return flask.url_for(USER_API_ENDPOINT, id=user_id)


def test_api_path(api, db_session):
    user = factories.create_user(db_session)
    response = api.get(USER_API_ENDPOINT, id=user.id)
    assert response.status_code == 200


class TestUserAPI:
    ## GET ##

    @pytest.mark.parametrize("as_self", [True, False])
    @pytest.mark.parametrize("fields", [None, "id,name,email", "name,email"])
    def test_get(self, as_self, fields, api, db_session):
        """Get a user's record, as either the user themself or as an admin."""
        user = factories.create_user(db_session, name="NAME", email="name@example.com")
        params = {"fields": fields} if fields is not None else {}
        if as_self is True:
            response = api.as_user(user).get(USER_API_ENDPOINT, id=user.id, **params)
        else:
            response = api.get(USER_API_ENDPOINT, id=user.id, **params)
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == user.id
        assert "password" not in data
        exp_data = {"name": "NAME", "email": "name@example.com"}
        assert {k: v for k, v in data.items() if k in exp_data} == exp_data

    def test_get_as_collaborator(self, api, db_session):
        """Get a user's record when they share a review with the current user."""
        reviewer, collaborator = factories.create_users(db_session, n=2)
        review = factories.create_review_with_team(
            db_session, owner=reviewer, members=[collaborator]
        )
        response = api.as_user(reviewer).get(USER_API_ENDPOINT, id=collaborator.id)
        assert response.status_code == 200
        assert response.json["id"] == collaborator.id

    def test_get_not_found(self, api):
        response = api.get(USER_API_ENDPOINT, id=NOT_FOUND_ID)
        assert response.status_code == 404

    def test_get_forbidden(self, api, db_session):
        """Get a user's record when they share nothing with the current user."""
        current_user, stranger = factories.create_users(db_session, n=2)
        response = api.as_user(current_user).get(USER_API_ENDPOINT, id=stranger.id)
        assert response.status_code == 403

    ## DELETE ##

    def test_delete_as_admin(self, api, db_session, admin_headers, client):
        user = factories.create_user(db_session)
        response = api.delete(USER_API_ENDPOINT, id=user.id)
        assert response.status_code == 204
        # verify with raw fixtures: `api` can only re-authenticate existing users
        assert (
            client.get(_user_url(client, user.id), headers=admin_headers).status_code
            == 404
        )  # not found!

    def test_delete_as_self(self, api, db_session, admin_headers, client):
        user = factories.create_user(db_session)
        response = api.as_user(user).delete(USER_API_ENDPOINT, id=user.id)
        assert response.status_code == 204
        assert (
            client.get(_user_url(client, user.id), headers=admin_headers).status_code
            == 404
        )  # not found!

    def test_delete_not_found(self, api):
        response = api.delete(USER_API_ENDPOINT, id=NOT_FOUND_ID)
        assert response.status_code == 404

    def test_delete_forbidden(self, api, db_session):
        """Delete another user, even one who collaborates on a shared review."""
        current_user = factories.create_user(db_session)
        collaborator = factories.create_user(db_session)
        review = factories.create_review(db_session)
        factories.add_review_user(db_session, review, current_user, role="member")
        factories.add_review_user(db_session, review, collaborator, role="member")
        response = api.as_user(current_user).delete(
            USER_API_ENDPOINT, id=collaborator.id
        )
        assert response.status_code == 403

    ## PUT ##

    @pytest.mark.parametrize(
        "data",
        [
            {"name": "NEW_NAME"},
            {"email": "new.name@example.com"},
            {"name": "NEW_NAME", "email": "new.name@example.com"},
            {"is_admin": True},
        ],
    )
    def test_put(self, data, api, db_session):
        """Modify another user's record, as an admin."""
        user = factories.create_user(db_session)
        response = api.put(USER_API_ENDPOINT, id=user.id, json=data)
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == user.id
        assert "password" not in obs_data
        assert {k: v for k, v in obs_data.items() if k in data} == data

    def test_put_not_found(self, api):
        response = api.put(
            USER_API_ENDPOINT, id=NOT_FOUND_ID, json={"name": "NEW_NAME"}
        )
        assert response.status_code == 404

    def test_put_forbidden(self, api, db_session):
        """Modify another user's record, as a regular user."""
        current_user, stranger = factories.create_users(db_session, n=2)
        response = api.as_user(current_user).put(
            USER_API_ENDPOINT, id=stranger.id, json={"name": "NEW_NAME"}
        )
        assert response.status_code == 403

    def test_put_admin_flag_forbidden(self, api, db_session):
        """Grant admin status to oneself, as a regular user."""
        user = factories.create_user(db_session)
        response = api.as_user(user).put(
            USER_API_ENDPOINT, id=user.id, json={"is_admin": True}
        )
        assert response.status_code == 403


class TestUsersAPI:
    def test_get_by_email(self, api, db_session):
        user = factories.create_user(db_session, email="user@example.com")
        _ = factories.create_user(db_session, email="rando@example.com")
        response = api.get(USERS_API_ENDPOINT, email=user.email)
        assert response.status_code == 200
        assert len(response.json) == 1
        assert response.json[0]["id"] == user.id
        assert response.json[0]["email"] == user.email

    def test_get_by_review(self, api, db_session):
        owner, member, other = factories.create_users(db_session, n=3)
        review = factories.create_review_with_team(
            db_session, owner=owner, members=[member]
        )
        response = api.get(USERS_API_ENDPOINT, review_id=review.id)
        assert response.status_code == 200
        # endpoint returns an unordered collection, so compare sets
        assert {user["id"] for user in response.json} == {owner.id, member.id}

    def test_get_admins(self, api):
        # the db_empty world creates exactly one admin, and these tests create
        # only regular users, so the admin list is exactly that one user
        response = api.get(USERS_API_ENDPOINT, admins=True)
        assert response.status_code == 200
        assert len(response.json) == 1
        assert response.json[0]["is_admin"] is True

    def test_get_errors(self, api, db_session):
        owner, outsider = factories.create_users(db_session, n=2)
        review = factories.create_review_with_team(db_session, owner=owner)
        assert (
            api.get(USERS_API_ENDPOINT, email="nobody@example.com").status_code == 404
        )
        assert api.get(USERS_API_ENDPOINT, review_id=NOT_FOUND_ID).status_code == 404
        assert (
            api.as_user(outsider)
            .get(USERS_API_ENDPOINT, review_id=review.id)
            .status_code
            == 403
        )
        assert (
            api.as_user(outsider).get(USERS_API_ENDPOINT, admins=True).status_code
            == 403
        )
