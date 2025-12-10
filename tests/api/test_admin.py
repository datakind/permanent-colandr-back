import flask
import pytest
import sqlalchemy as sa

from colandr.api.v1 import authn

from .. import helpers


GET_REVIEWS_API_ENDPOINT = "admin.get_reviews"
POST_USERS_API_ENDPOINT = "admin.post_users"


@pytest.mark.usefixtures("db_session")
class TestGetReviewsAPI:
    @pytest.mark.parametrize(
        ["review_ids", "num_exp"],
        [("1", 1), ("1,2", 2), ("1,2,99", 2)],
    )
    def test_get(self, review_ids, num_exp, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(GET_REVIEWS_API_ENDPOINT, review_ids=review_ids)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert len(data) == num_exp


@pytest.mark.usefixtures("db_session")
class TestPostUsersAPI:
    @pytest.mark.parametrize(
        "data",
        [
            {
                "name": "NAMEX",
                "email": "namex@example.net",
                "password": "PASSWORDX",
            },
        ],
    )
    def test_post(self, data, app, client, db_session, admin_headers):
        # NOTE: we specify user ids in the seed data, but apparently the auto-increment
        # sequence isn't made aware of it; so, we need to manually bump the start value
        # so that this created user isn't assigned id=1, which is already in use
        # and so violates a unique constraint. seems crazy, but here we are
        db_session.execute(sa.text("ALTER SEQUENCE users_id_seq RESTART WITH 6"))
        with app.test_request_context():
            url = flask.url_for(POST_USERS_API_ENDPOINT)
        response = client.post(url, json=data, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert data["email"] == response_data["email"]

    @pytest.mark.parametrize(
        ["current_user_id", "data", "status_code"],
        [
            (1, {"name": "NAMEX", "email": "namex@example.net"}, 422),
            (1, {"email": "namex@example.net", "password": "PASSWORDX"}, 422),
            (1, {"name": "NAMEX", "password": "PASSWORDX"}, 422),
            (
                2,
                {
                    "name": "NAMEX",
                    "email": "namex@example.net",
                    "password": "PASSWORDX",
                },
                422,
            ),
        ],
    )
    def test_post_errors(
        self, current_user_id, data, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for(POST_USERS_API_ENDPOINT)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.post(
                    url, data=data, headers=authn.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code
