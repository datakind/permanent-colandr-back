import urllib.parse

import pytest


class TestUserResource:

    @pytest.mark.parametrize(
        ["id_", "params"],
        [
            (1, None),
            (1, {"fields": "id,name,email"})
        ],
    )
    def test_get(self, id_, params, app, client, admin_user, admin_headers):
        url = f"/api/users/{id_}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200

        data = response.json
        fields = None if params is None else params["fields"].split(",")
        assert "id" in data
        assert "password" not in data
        assert data["id"] == id_
        if fields is None or "email" in fields:
            assert data["email"] == admin_user.email
        if fields is None or "is_admin" in fields:
            assert data["is_admin"] is True
        if fields:
            assert sorted(data.keys()) == sorted(fields)
