"""Tests for the auth API."""

import flask
import flask_jwt_extended as jwtext
import pytest
import sqlalchemy as sa

from colandr import models
from colandr.api.v1 import authn

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

LOGIN_API_ENDPOINT = "auth.login"
LOGOUT_API_ENDPOINT = "auth.logout"
REFRESH_API_ENDPOINT = "auth.refresh"
REGISTER_API_ENDPOINT = "auth.register"
REGISTER_RESEND_API_ENDPOINT = "auth.register_resend"
REGISTER_CONFIRM_API_ENDPOINT = "auth.register_confirm"
RESET_API_ENDPOINT = "auth.reset"
RESET_CONFIRM_API_ENDPOINT = "auth.reset_confirm"
# a review-scoped route, used to show what a token can and can't reach
REVIEW_PROGRESS_API_ENDPOINT = "review_progress.review_progress"


def _bearer_headers(token: str) -> dict[str, str]:
    """Pack a raw JWT into the app's auth header, for tokens the fixtures can't mint."""
    config = flask.current_app.config
    return {config["JWT_HEADER_NAME"]: f"{config['JWT_HEADER_TYPE']} {token}"}


@pytest.fixture
def graph(db_session, admin_user):
    """Three users and the review one of them belongs to.

    user1 is a confirmed member of review1; user2 is confirmed but on no team;
    unconfirmed user registered but never confirmed. Passwords are load-bearing.
    """
    user1 = factories.create_user(
        db_session, email="user1@example.com", password="PASSWORD1"
    )
    user2 = factories.create_user(
        db_session, email="user2@example.com", password="PASSWORD2"
    )
    unconfirmed = factories.create_user(
        db_session, email="x@example.com", password="PASSWORDX", is_confirmed=False
    )
    review1 = factories.create_review_with_team(
        db_session, owner=admin_user, members=[user1]
    )
    return {
        "user1": user1,
        "user2": user2,
        "unconfirmed": unconfirmed,
        "review1": review1,
    }


class TestLoginAPI:
    @pytest.mark.parametrize(
        ["user_key", "email", "password", "status_code"],
        [
            ("user1", None, "PASSWORD1", 200),
            ("user1", None, "WRONG_PASSWORD", 404),
            (None, "nobody@example.com", "PASSWORD1", 404),
            # FIXME: an unconfirmed user logs in successfully and gets usable tokens;
            # the 401 in LoginAPI is commented out. Should be 403 until confirmed?
            ("unconfirmed", None, "PASSWORDX", 200),
        ],
    )
    def test_post(self, user_key, email, password, status_code, graph, api):
        """Log-in with good, wrong, and unknown credentials."""
        if email is None:
            email = graph[user_key].email
        response = api.post(
            LOGIN_API_ENDPOINT, json={"email": email, "password": password}, headers={}
        )
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            assert set(response.json) == {"access_token", "refresh_token"}
            assert all(response.json.values())

    @pytest.mark.parametrize(
        "json_body",
        [
            {"password": "PASSWORD1"},
            {"email": "user1@example.com"},
            {"email": "not-an-email", "password": "PASSWORD1"},
        ],
        ids=["no-email", "no-password", "bad-email"],
    )
    def test_post_invalid(self, json_body, api):
        """Reject a login body that fails schema validation."""
        response = api.post(LOGIN_API_ENDPOINT, json=json_body, headers={})
        assert response.status_code == 422

    def test_unconfirmed_token_reaches_unguarded_endpoints_only(self, graph, api):
        """An unconfirmed user's token is refused wherever authz checks is_confirmed.

        FIXME: this token should never exist -- see the ``unconfirmed`` row above.
        Both authz predicates require ``is_confirmed``, so the blast radius is the
        token-only endpoints (logout, refresh, register/resend), not review data.
        """
        login = api.post(
            LOGIN_API_ENDPOINT,
            json={"email": graph["unconfirmed"].email, "password": "PASSWORDX"},
            headers={},
        )
        headers = _bearer_headers(login.json["access_token"])
        reg_response = api.post(REGISTER_RESEND_API_ENDPOINT, headers=headers)
        assert reg_response.status_code == 200
        prog_response = api.get(
            REVIEW_PROGRESS_API_ENDPOINT, id=graph["review1"].id, headers=headers
        )
        assert prog_response.status_code == 403


class TestLogoutAPI:
    def test_delete_revokes_token(self, graph, api):
        """A token stops working once the client logs out with it."""
        headers = authn.pack_header_for_user(graph["user1"])
        before = api.get(
            REVIEW_PROGRESS_API_ENDPOINT, id=graph["review1"].id, headers=headers
        )
        assert before.status_code == 200

        response = api.delete(LOGOUT_API_ENDPOINT, headers=headers)
        assert response.status_code == 200
        assert response.json["message"] == f"{graph['user1']} logged out"

        after = api.get(
            REVIEW_PROGRESS_API_ENDPOINT, id=graph["review1"].id, headers=headers
        )
        assert after.status_code == 401

    def test_delete_accepts_refresh_token(self, graph, api):
        """Logout verifies no token type (``verify_type=False``), so refresh works too."""
        token = jwtext.create_refresh_token(identity=graph["user1"])
        response = api.delete(LOGOUT_API_ENDPOINT, headers=_bearer_headers(token))
        assert response.status_code == 200

    def test_delete_anonymous(self, api):
        """A request with no token can't log anyone out."""
        response = api.delete(LOGOUT_API_ENDPOINT, headers={})
        assert response.status_code == 401


class TestRefreshTokenAPI:
    def test_get(self, graph, api):
        """A refresh token creates a new access token that works on protected routes."""
        token = jwtext.create_refresh_token(identity=graph["user1"])
        response = api.get(REFRESH_API_ENDPOINT, headers=_bearer_headers(token))
        assert response.status_code == 200
        assert set(response.json) == {"access_token"}

        access_token = response.json["access_token"]
        response = api.get(
            REVIEW_PROGRESS_API_ENDPOINT,
            id=graph["review1"].id,
            headers=_bearer_headers(access_token),
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ["token_kind", "status_code"],
        [("access", 422), ("garbage", 422), ("none", 401)],
        ids=["wrong-token-type", "undecodable", "no-credentials"],
    )
    def test_get_invalid(self, token_kind, status_code, graph, api):
        """Reject anything that isn't a usable refresh token."""
        headers = (
            authn.pack_header_for_user(graph["user1"])
            if token_kind == "access"
            else _bearer_headers("not-a-jwt")
            if token_kind == "garbage"
            else {}
        )
        response = api.get(REFRESH_API_ENDPOINT, headers=headers)
        assert response.status_code == status_code


class TestRegisterAPI:
    def test_post(self, api, db_session, enqueued):
        """Register a new user: persisted, unconfirmed, no mail sent by default."""
        data = {"name": "NAMEX", "email": "namex@example.com", "password": "PASSWORDX"}
        response = api.post(REGISTER_API_ENDPOINT, json=data, headers={})
        assert response.status_code == 200
        assert response.json["name"] == data["name"]
        assert response.json["email"] == data["email"]
        assert "password" not in response.json
        # FIXME: a registrant is immediately issued tokens (see TestLoginAPI), so
        # confirmation is only advisory. Should be unusable until is_confirmed?
        assert response.json["is_confirmed"] is False

        user = (
            db_session.execute(sa.select(models.User).filter_by(email=data["email"]))
            .scalars()
            .one_or_none()
        )
        assert user is not None
        assert user.check_password(data["password"]) is True
        # MAIL_SERVER is pinned to None, so the confirmation email is never enqueued
        assert enqueued["send_email"] == []

    def test_post_sends_confirmation_mail_when_configured(
        self, api, app, monkeypatch, enqueued
    ):
        """With a mail server configured, registration enqueues one email."""
        monkeypatch.setitem(app.config, "MAIL_SERVER", "smtp.example.com")
        data = {"name": "NAMEX", "email": "namex@example.com", "password": "PASSWORDX"}
        response = api.post(REGISTER_API_ENDPOINT, json=data, headers={})
        assert response.status_code == 200
        assert len(enqueued["send_email"]) == 1
        assert enqueued["send_email"][0]["args"][0] == [data["email"]]

    def test_post_duplicate_email(self, graph, api):
        """Reject a registration whose email is already taken."""
        data = {"name": "DUPE", "email": graph["user1"].email, "password": "PASSWORD1"}
        response = api.post(REGISTER_API_ENDPOINT, json=data, headers={})
        assert response.status_code == 403

    @pytest.mark.parametrize(
        "body",
        [
            {"email": "namex@example.com", "password": "PASSWORDX"},
            {"name": "NAMEX", "password": "PASSWORDX"},
            {"name": "NAMEX", "email": "namex@example.com"},
            {"name": "NAMEX", "email": "namex@example.com", "password": "SHORT"},
        ],
        ids=["no-name", "no-email", "no-password", "short-password"],
    )
    def test_post_invalid(self, body, api):
        """Reject a registration body that fails schema validation."""
        response = api.post(REGISTER_API_ENDPOINT, json=body, headers={})
        assert response.status_code == 422


class TestRegisterResendAPI:
    def test_post(self, graph, api):
        """Re-send confirmation email for the current user."""
        headers = authn.pack_header_for_user(graph["unconfirmed"])
        response = api.post(REGISTER_RESEND_API_ENDPOINT, headers=headers)
        assert response.status_code == 200

    def test_post_anonymous(self, api):
        """Route needs a token to know who to mail."""
        response = api.post(REGISTER_RESEND_API_ENDPOINT, headers={})
        assert response.status_code == 401


class TestRegisterConfirmAPI:
    def test_get(self, graph, api):
        """A token from the confirmation email marks the user as confirmed."""
        token = jwtext.create_access_token(identity=graph["unconfirmed"])
        response = api.get(REGISTER_CONFIRM_API_ENDPOINT, token=token, headers={})
        assert response.status_code == 200
        assert set(response.json) == {"access_token"}
        assert graph["unconfirmed"].is_confirmed is True

    def test_get_garbage_token(self, api):
        """Reject a token that isn't a decodable JWT."""
        response = api.get(REGISTER_CONFIRM_API_ENDPOINT, token="not-a-jwt", headers={})
        assert response.status_code == 422

    def test_get_token_for_missing_user(self, api, db_session):
        """A well-formed token whose user is missing yields a 404."""
        user = factories.create_user(db_session)
        token = jwtext.create_access_token(identity=user)
        db_session.delete(user)
        db_session.flush()
        response = api.get(REGISTER_CONFIRM_API_ENDPOINT, token=token, headers={})
        assert response.status_code == 404


class TestResetPasswordAPI:
    def test_post(self, graph, api, app, monkeypatch, enqueued):
        """A known email gets a reset email enqueued when mail is configured."""
        monkeypatch.setitem(app.config, "MAIL_SERVER", "smtp.example.com")
        response = api.post(RESET_API_ENDPOINT, email=graph["user1"].email, headers={})
        assert response.status_code == 200
        assert len(enqueued["send_email"]) == 1
        assert enqueued["send_email"][0]["args"][0] == [graph["user1"].email]

    def test_post_unknown_email(self, api, enqueued):
        """An unknown email gets an empty 200, so accounts can't be enumerated."""
        response = api.post(RESET_API_ENDPOINT, email="someone@example.com", headers={})
        assert response.status_code == 200
        assert enqueued["send_email"] == []

    def test_post_invalid_email(self, api):
        """Request with an invalid email address is rejected."""
        response = api.post(RESET_API_ENDPOINT, email="not-an-email", headers={})
        assert response.status_code == 422


class TestResetPasswordConfirmAPI:
    def test_put(self, graph, api):
        """A reset token sets a new password that then works for login."""
        token = jwtext.create_access_token(identity=graph["user1"])
        reset_response = api.put(
            RESET_CONFIRM_API_ENDPOINT,
            token=token,
            json={"password": "NEW_PASSWORD"},
            headers={},
        )
        assert reset_response.status_code == 200
        login_response = api.post(
            LOGIN_API_ENDPOINT,
            json={"email": graph["user1"].email, "password": "NEW_PASSWORD"},
            headers={},
        )
        assert login_response.status_code == 200

    def test_put_unconfirmed_user(self, graph, api):
        """An unconfirmed user must confirm the address before resetting a password."""
        token = jwtext.create_access_token(identity=graph["unconfirmed"])
        response = api.put(
            RESET_CONFIRM_API_ENDPOINT,
            token=token,
            json={"password": "NEW_PASSWORD"},
            headers={},
        )
        assert response.status_code == 403

    def test_put_garbage_token(self, api):
        """Reject a token that isn't a decodable JWT."""
        response = api.put(
            RESET_CONFIRM_API_ENDPOINT,
            token="not-a-jwt",
            json={"password": "NEW_PASSWORD"},
            headers={},
        )
        assert response.status_code == 422

    def test_put_short_password(self, graph, api):
        """Reject a password shorter than the schema's floor."""
        token = jwtext.create_access_token(identity=graph["user1"])
        response = api.put(
            RESET_CONFIRM_API_ENDPOINT,
            token=token,
            json={"password": "SHORT"},
            headers={},
        )
        assert response.status_code == 422
