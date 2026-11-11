"""Tests for the authn helpers."""

import datetime
import os
import time
from unittest import mock

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


class TestAddToBlocklist:
    def test_sets_key_with_ttl(self):
        mock_redis = mock.MagicMock()
        with mock.patch.object(authn, "_get_redis_client", return_value=mock_redis):
            authn._add_to_blocklist("jti-001", ttl_seconds=3600)
        mock_redis.set.assert_called_once_with("jwt_blocklist:jti-001", "1", ex=3600)

    def test_redis_unavailable_logs_and_returns(self, caplog):
        mock_redis = mock.MagicMock()
        mock_redis.set.side_effect = ConnectionError("boom")
        with mock.patch.object(authn, "_get_redis_client", return_value=mock_redis):
            authn._add_to_blocklist("jti-001", ttl_seconds=3600)
        assert any("Cannot add token to blocklist" in r.message for r in caplog.records)


class TestIsBlocklisted:
    @pytest.mark.parametrize(
        ["exists", "expected"],
        [(1, True), (0, False)],
    )
    def test_returns_expected(self, exists, expected):
        mock_redis = mock.MagicMock()
        mock_redis.exists.return_value = exists
        with mock.patch.object(authn, "_get_redis_client", return_value=mock_redis):
            assert authn._is_blocklisted("jti-001") is expected

    def test_fails_open_on_redis_error(self, caplog):
        mock_redis = mock.MagicMock()
        mock_redis.exists.side_effect = ConnectionError("boom")
        with mock.patch.object(authn, "_get_redis_client", return_value=mock_redis):
            assert authn._is_blocklisted("jti-001") is False
        assert any("Cannot check token blocklist" in r.message for r in caplog.records)


class TestRevokeToken:
    def test_computes_ttl_from_exp_claim(self):
        mock_add = mock.MagicMock()
        now = int(time.time())
        jwt_data = {"jti": "jti-002", "exp": now + 1800}
        with mock.patch.object(authn, "_add_to_blocklist", mock_add):
            authn.revoke_token(jwt_data)
        called_ttl = mock_add.call_args[0][1]
        assert 1795 <= called_ttl <= 1805

    def test_skips_expired_token(self):
        mock_add = mock.MagicMock()
        now = int(time.time())
        jwt_data = {"jti": "jti-003", "exp": now - 60}
        with mock.patch.object(authn, "_add_to_blocklist", mock_add):
            authn.revoke_token(jwt_data)
        mock_add.assert_not_called()
