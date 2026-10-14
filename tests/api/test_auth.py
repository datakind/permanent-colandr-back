"""Auth helper tests."""

import datetime
import os

import flask_jwt_extended as jwtext
import pytest

from colandr.api.v1 import authn

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")


def test_get_user_from_token(db_session):
    user1 = factories.create_user(db_session)
    user2 = factories.create_user(db_session, is_admin=True)
    for user in (user1, user2):
        token = jwtext.create_access_token(
            identity=user, fresh=True, expires_delta=datetime.timedelta(seconds=30)
        )
        assert authn.get_user_from_token(token) is user


def test_pack_header_for_user(db_session):
    for user in factories.create_users(db_session, n=2):
        header = authn.pack_header_for_user(user)
        assert isinstance(header, dict)
        assert "Authorization" in header
        assert header["Authorization"].startswith("Bearer")


@pytest.mark.skipif(
    not os.environ.get("COLANDR_REDIS_HOST"),
    reason="Redis not available; blocklist is a no-op without it",
)
def test_logout_revokes_token(admin_user, client):
    """A token used after logout should be rejected.

    Uses a fresh token created specifically for this test -- *not* the session-scoped
    admin_headers fixture -- because this test revokes the token,
    which many subsequent tests need in order to function.
    """
    headers = authn.pack_header_for_user(admin_user)

    resp = client.get("/api/reviews/", headers=headers)
    assert resp.status_code == 200

    resp = client.delete("/api/auth/logout", headers=headers)
    assert resp.status_code == 200

    resp = client.get("/api/reviews/", headers=headers)
    assert resp.status_code == 401
