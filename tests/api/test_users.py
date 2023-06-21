import urllib.parse

import flask
import pytest

from colandr import extensions, models


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
    def test_get(self, id_, params, status_code, client, admin_headers, seed_data):
        url = f"/api/users/{id_}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
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
    def test_delete(self, id_, client, admin_user, admin_headers, db_session):
        url = f"/api/users/{id_}"
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
            (2, {"name": "NEW_USER_NAME2"}, 200),
            (3, {"email": "name3@newdomain.com"}, 200),
            (4, {"name": "NEW_USER_NAME4", "email": "name4@newdomain.com"}, 200),
            # TODO: fix this case! flask praetorian can't pack header for nonexistent user
            # (999, {"name": "NEW_USER_NAME999"}, 403),
        ],
    )
    def test_put(
        self, id_, params, status_code, client, admin_user, admin_headers, db_session
    ):
        url = f"/api/users/{id_}?{urllib.parse.urlencode(params)}"
        # only user can modify themself
        response = client.put(url, headers=admin_headers)
        assert response.status_code == 403
        # now we check it
        user = db_session.query(models.User).get(id_)
        user_headers = extensions.guard.pack_header_for_user(user)
        flask.g.current_user = user
        response = client.put(url, headers=user_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in params.items():
                assert data.get(key) == val
        # reset current user to admin
        flask.g.current_user = admin_user
