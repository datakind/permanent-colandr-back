import flask
import pytest
import sqlalchemy as sa

from colandr.apis import auth

from .. import helpers


def test_api_path(client, admin_headers):
    url = "/api/users/1"
    response = client.get(url, headers=admin_headers)
    assert response.status_code == 200


@pytest.mark.usefixtures("db_session")
class TestUserResource:
    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "params", "exp_data"],
        [
            (
                1,
                1,
                None,
                {
                    "name": "NAME1",
                    "email": "name1@example.com",
                    "is_confirmed": True,
                    "is_admin": True,
                },
            ),
            (
                1,
                2,
                None,
                {
                    "name": "NAME2",
                    "email": "name2@example.com",
                    "is_confirmed": True,
                    "is_admin": False,
                },
            ),
            (
                2,
                3,
                None,
                {
                    "name": "NAME3",
                    "email": "name3@example.com",
                    "is_confirmed": True,
                    "is_admin": False,
                },
            ),
            (
                1,
                1,
                {"fields": "id,name,email"},
                {"name": "NAME1", "email": "name1@example.com"},
            ),
            (
                2,
                2,
                {"fields": "name,email"},
                {"name": "NAME2", "email": "name2@example.com"},
            ),
        ],
    )
    def test_get(
        self, current_user_id, user_id, params, exp_data, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=user_id, **(params or {}))
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.get(
                    url, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == user_id
        assert "password" not in data
        assert {k: v for k, v in data.items() if k in exp_data} == exp_data

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "params", "status_code"],
        [
            (1, 999, None, 404),
            (4, 1, None, 403),
        ],
    )
    def test_get_errors(
        self, current_user_id, user_id, params, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=user_id, **(params or {}))
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.get(
                    url, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "user_id"],
        [
            (1, 2),
            (3, 3),
        ],
    )
    def test_delete(
        self, current_user_id, user_id, app, client, db_session, admin_headers
    ):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=user_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.delete(url, headers=headers)
                assert response.status_code == 204
        assert client.get(url, headers=admin_headers).status_code == 404  # not found!

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "status_code"],
        [
            (1, 999, 404),
            (2, 3, 403),
        ],
    )
    def test_delete_errors(
        self, current_user_id, user_id, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=user_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.delete(
                    url, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "data"],
        [
            (1, 2, {"name": "NEW_NAME2"}),
            (1, 3, {"email": "name3@example.net"}),
            (1, 4, {"name": "NEW_NAME4", "email": "name4@example.net"}),
        ],
    )
    def test_put(self, current_user_id, user_id, data, app, client, db_session):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=user_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.put(
                    url, json=data, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == user_id
        assert "password" not in obs_data
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "data", "status_code"],
        [
            (3, 2, {"name": "NEW_NAME2"}, 403),
            (1, 999, {"name": "NEW_NAME999"}, 404),
            # TODO: figure out if there's a way to throw nice errors
            # in case "current user" doesn't actually exist
            # (999, 999, {"name": "NEW_NAME999"}, 404),
        ],
    )
    def test_put_errors(
        self, current_user_id, user_id, data, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=user_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.put(
                    url, json=data, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code


@pytest.mark.usefixtures("db_session")
class TestUsersResource:
    @pytest.mark.parametrize(
        ["email", "review_id", "user_ids"],
        [
            ("name1@example.com", None, 1),
            ("name2@example.com", 1, 2),
            (None, 1, [1, 2, 3]),
        ],
    )
    def test_get(self, email, review_id, user_ids, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "users_users_resource", email=email, review_id=review_id
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        if email is not None:
            assert isinstance(data, dict)
            assert data["id"] == user_ids
            assert data["email"] == email
        elif review_id is not None:
            assert isinstance(data, list)
            assert [user["id"] for user in data] == user_ids

    @pytest.mark.parametrize(
        ["current_user_id", "email", "review_id", "status_code"],
        [
            (1, "name999@example.com", None, 404),
            (1, None, 999, 404),
            (4, None, 1, 403),
        ],
    )
    def test_get_errors(
        self, current_user_id, email, review_id, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for(
                "users_users_resource", email=email, review_id=review_id
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.get(
                    url, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

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
            url = flask.url_for("users_users_resource")
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
            url = flask.url_for("users_users_resource")
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.post(
                    url, data=data, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code
