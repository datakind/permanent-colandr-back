"""Verification tests for the ``db`` and ``db_session`` fixtures.

These tests exist to catch regressions in the test infrastructure itself: if
the savepoint-and-rollback machinery in ``conftest.db_session`` ever stops
isolating writes between tests, these will fail loudly.
"""

import flask
import pytest
import sqlalchemy as sa

from colandr import models
from colandr.extensions import db


TARGET_USER_ID = 4
USER_API_ENDPOINT = "users.user"


def test_db_connection(app):
    with app.app_context():
        with db.engine.connect() as conn:
            _ = conn.execute(sa.text("SELECT 1"))


@pytest.mark.usefixtures("db_session")
class TestDbIsolationViaApi:
    """Verify writes made through the Flask test client are rolled back."""

    def test_api_write_visible_within_test(
        self, app, client, db_session, admin_headers
    ):
        """A DELETE through the API must be visible to subsequent reads in the same test."""
        with app.test_request_context():
            url = flask.url_for(USER_API_ENDPOINT, id=TARGET_USER_ID)

        # sanity check: user exists at the start of the test
        pre = db_session.get(models.User, TARGET_USER_ID)
        assert pre is not None, f"seed data is missing user id={TARGET_USER_ID}"
        # write through the API (full Flask request cycle, not direct ORM)
        response = client.delete(url, headers=admin_headers)
        assert response.status_code == 204
        # write must be visible to a subsequent API read in the same test
        # if db_session is not actually intercepting the request's session
        # the delete went somewhere else and this GET would still return 200
        get_response = client.get(url, headers=admin_headers)
        assert get_response.status_code == 404

    def test_api_write_rolled_back_across_tests(
        self, app, client, db_session, admin_headers
    ):
        """The DELETE from prior test must NOT have leaked into this test."""
        with app.test_request_context():
            url = flask.url_for(USER_API_ENDPOINT, id=TARGET_USER_ID)

        # if isolation works, prior tests's transaction was rolled back during teardown
        # and the user is back; if isolation is broken, this fails
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200, (
            "API isolation is broken: a write from a previous test leaked. "
            "Check the db_session fixture's engine-shim and rollback teardown."
        )
        assert response.json["id"] == TARGET_USER_ID
        # also confirm via direct session read, in case the API path is somehow reading
        # from a different session than the one db_session yielded
        user = db_session.get(models.User, TARGET_USER_ID)
        assert user is not None


@pytest.mark.usefixtures("db_session")
class TestDbIsolationViaSession:
    """Verify writes made directly through ``db_session`` are rolled back."""

    def test_direct_write_visible_within_test(self, db_session):
        user = db_session.get(models.User, TARGET_USER_ID)
        assert user is not None
        original_name = user.name

        user.name = "ISOLATION_PROBE_NAME"
        db_session.flush()
        # re-fetch to confirm the write is visible on this session
        refetched = db_session.get(models.User, TARGET_USER_ID)
        assert refetched.name == "ISOLATION_PROBE_NAME"
        assert original_name != "ISOLATION_PROBE_NAME"

    def test_direct_write_rolled_back_across_tests(self, db_session):
        user = db_session.get(models.User, TARGET_USER_ID)
        assert user is not None
        assert user.name != "ISOLATION_PROBE_NAME", (
            "Direct-session isolation is broken! A write from the previous test "
            "was not rolled back. Check that db_session's outer transaction.rollback() "
            "is actually executing in teardown."
        )
