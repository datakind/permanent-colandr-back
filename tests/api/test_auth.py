import datetime
import os

import flask_jwt_extended as jwtext
import pytest

from colandr import models
from colandr.api.v1 import authn


@pytest.mark.parametrize("user_id", [2, 3])
def test_get_user_from_token(user_id, db_session):
    orig_user = db_session.get(models.User, user_id)
    token = jwtext.create_access_token(
        identity=orig_user, fresh=True, expires_delta=datetime.timedelta(seconds=30)
    )
    user = authn.get_user_from_token(token)
    assert user is orig_user


@pytest.mark.parametrize("user_id", [2, 3])
def test_pack_header_for_user(user_id, db_session):
    user = db_session.get(models.User, user_id)
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
