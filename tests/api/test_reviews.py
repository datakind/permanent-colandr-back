import urllib.parse

import flask
import pytest

from colandr import extensions, models


class TestReviewResource:

    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, None, 200),
            (2, None, 200),
            (1, {"fields": "id,name"}, 200),
            (1, {"fields": "description"}, 200),
            (999, None, 404),
        ],
    )
    def test_get(self, id_, params, status_code, client, admin_headers, seed_data):
        url = f"/api/reviews/{id_}"
        if params:
            url = f"{url}?{urllib.parse.urlencode(params)}"
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            seed_data = seed_data["reviews"][id_ - 1]
            fields = None if params is None else params["fields"].split(",")
            if fields is not None and "id" not in fields:
                fields.append("id")
            assert "id" in data
            assert data["id"] == id_
            for field in ["name", "description"]:
                if fields is None or field in fields:
                    assert data[field] == seed_data.get(field)
            if fields:
                assert sorted(data.keys()) == sorted(fields)

    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, {"name": "NEW_REVIEW_NAME1"}, 200),
            (1, {"description": "NEW_DESCRIPTION1"}, 200),
            (2, {"name": "NEW_REVIEW_NAME2", "description": "NEW_DESCRIPTION2"}, 200),
            (999, {"name": "NEW_REVIEW_NAME999"}, 404),
        ],
    )
    def test_put(self, id_, params, status_code, client, admin_user, admin_headers, db_session):
        url = f"/api/reviews/{id_}?{urllib.parse.urlencode(params)}"
        response = client.put(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in params.items():
                assert data.get(key) == val
