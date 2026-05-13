"""Tests for (Redis-backed) JWT blocklist operations."""

import time
from unittest import mock

import pytest

from colandr.api.v1 import authn


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
