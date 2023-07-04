import flask
import pytest

from colandr import extensions, models


def test_api_path(client, admin_headers):
    url = "/api/users/1"
    response = client.get(url, headers=admin_headers)
    assert response.status_code == 200


class TestUsersResource:
    @pytest.mark.parametrize(
        ["email", "review_id", "num_exp"],
        [
            ("name1@example.com", None, 1),
            ("name2@example.com", 1, 1),
            # TODO: figure out the user<=>review mapping in seed data
            # (None, 1, 2),
        ],
    )
    def test_get(self, email, review_id, num_exp, app, client, admin_headers):
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
            assert data["email"] == email
        elif review_id is not None:
            assert isinstance(data, list)
            assert len(data) == num_exp

    @pytest.mark.parametrize(
        "data",
        [
            {"name": "NAMEX", "email": "namex@example.net", "password": "PASSWORD"},
        ],
    )
    def test_post(self, data, app, client, db_session, admin_headers):
        with app.test_request_context():
            url = flask.url_for("users_users_resource")
        response = client.post(url, json=data, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert data["email"] == response_data["email"]

    @pytest.mark.parametrize(
        ["data", "status_code"],
        [
            ({"name": "NAMEX", "email": "namex@example.net"}, 422),
            ({"email": "namex@example.net", "password": "PASSWORD"}, 422),
            ({"name": "NAMEX", "password": "PASSWORD"}, 422),
        ],
    )
    def test_post_error(self, data, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("users_users_resource")
        response = client.post(url, data=data, headers=admin_headers)
        assert response.status_code == status_code


class TestUserResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, None, 200),
            (2, None, 200),
            (3, None, 200),
            (2, {"fields": "id,name,email"}, 200),
            (2, {"fields": "name,email"}, 200),
            (999, None, 404),
        ],
    )
    def test_get(self, id_, params, status_code, app, client, admin_headers, seed_data):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=id_, **(params or {}))
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            seed_user = seed_data["users"][id_ - 1]
            fields = None if params is None else params["fields"].split(",")
            if fields is not None and "id" not in fields:
                fields.append("id")
            assert "id" in data
            assert "password" not in data
            assert data["id"] == id_
            if fields is None or "email" in fields:
                assert data["email"] == seed_user.get("email")
            if fields is None or "is_confirmed" in fields:
                assert data["is_confirmed"] is seed_user.get("is_confirmed", False)
            if fields is None or "is_admin" in fields:
                assert data["is_admin"] is seed_user.get("is_admin", False)
            if fields:
                assert sorted(data.keys()) == sorted(fields)

    @pytest.mark.parametrize("id_", [2, 3])
    def test_delete(self, id_, app, client, admin_user, admin_headers, db_session):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=id_)
        # only user can delete themself
        response = client.delete(url, headers=admin_headers)
        assert response.status_code == 403
        # now we check it
        user = db_session.query(models.User).get(id_)
        user_headers = extensions.guard.pack_header_for_user(user)
        flask.g.current_user = user
        response = client.delete(url, headers=user_headers)
        assert response.status_code == 204
        # reset current user to admin
        flask.g.current_user = admin_user

    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (2, {"name": "NEW_NAME2"}, 200),
            (3, {"email": "name3@example.net"}, 200),
            (4, {"name": "NEW_NAME4", "email": "name4@example.net"}, 200),
            # TODO: fix this case! flask praetorian can't pack header for nonexistent user
            # (999, {"name": "NEW_NAME999"}, 403),
        ],
    )
    def test_put(
        self,
        id_,
        params,
        status_code,
        app,
        client,
        admin_user,
        admin_headers,
        db_session,
    ):
        with app.test_request_context():
            url = flask.url_for("users_user_resource", id=id_)
        # only user can modify themself
        response = client.put(url, json=params, headers=admin_headers)
        assert response.status_code == 403
        # now we check it
        user = db_session.query(models.User).get(id_)
        user_headers = extensions.guard.pack_header_for_user(user)
        flask.g.current_user = user
        response = client.put(url, json=params, headers=user_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in params.items():
                assert data.get(key) == val
        # reset current user to admin
        flask.g.current_user = admin_user
