import flask
import pytest


@pytest.mark.usefixtures("db_session")
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
    def test_get(self, id_, params, status_code, app, client, admin_headers, seed_data):
        with app.test_request_context():
            url = flask.url_for("reviews_review_resource", id=id_, **(params or {}))
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
    def test_put(self, id_, params, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("reviews_review_resource", id=id_)
        response = client.put(url, json=params, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in params.items():
                assert data.get(key) == val

    @pytest.mark.parametrize("id_", [1, 2])
    def test_delete(self, id_, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("reviews_review_resource", id=id_)
        response = client.delete(url, headers=admin_headers)
        assert response.status_code == 204
        get_response = client.get(url, headers=admin_headers)
        assert get_response.status_code == 404  # not found!


class TestReviewsResource:
    @pytest.mark.parametrize(
        ["_review_ids", "num_exp"],
        [("1", 1), ("1,2", 2), ("1,2,99", 2)],
    )
    def test_get(self, _review_ids, num_exp, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("reviews_reviews_resource", _review_ids=_review_ids)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert len(data) == num_exp

    @pytest.mark.parametrize(
        "data",
        [
            {"name": "NAMEX", "description": "DESCX"},
        ],
    )
    def test_post(self, data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("reviews_reviews_resource")
        response = client.post(url, json=data, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert data["name"] == response_data["name"]

    @pytest.mark.parametrize(
        ["data", "status_code"],
        [
            ({"name": None, "description": "DESCX"}, 422),
        ],
    )
    def test_post_error(self, data, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("reviews_reviews_resource")
        response = client.post(url, json=data, headers=admin_headers)
        assert response.status_code == status_code
