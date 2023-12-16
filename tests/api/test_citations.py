import flask
import pytest


@pytest.mark.usefixtures("db_session")
class TestCitationResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, None, 200),
            (2, None, 200),
            (1, {"fields": "id,title"}, 200),
            (1, {"fields": "abstract"}, 200),
            (999, None, 404),
        ],
    )
    def test_get(self, id_, params, status_code, app, client, admin_headers, seed_data):
        with app.test_request_context():
            url = flask.url_for("citations_citation_resource", id=id_, **(params or {}))
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            seed_data = seed_data["citations"][id_ - 1]
            fields = None if params is None else params["fields"].split(",")
            if fields is not None and "id" not in fields:
                fields.append("id")
            assert "id" in data
            assert data["id"] == id_
            for field in ["title", "abstract"]:
                if fields is None or field in fields:
                    assert data[field] == seed_data.get(field)
            if fields:
                assert sorted(data.keys()) == sorted(fields)

    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, {"title": "NEW_TITLE1"}, 200),
            (1, {"abstract": "NEW_ABSTRACT1"}, 200),
            (2, {"title": "NEW_TITLE2", "abstract": "NEW_ABSTRACT2"}, 200),
            (999, {"title": "NEW_TITLE999"}, 404),
        ],
    )
    def test_put(self, id_, params, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("citations_citation_resource", id=id_)
        response = client.put(url, json=params, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in params.items():
                assert data.get(key) == val

    @pytest.mark.parametrize("id_", [1, 2])
    def test_delete(self, id_, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("citations_citation_resource", id=id_)
        response = client.delete(url, headers=admin_headers)
        assert response.status_code == 204
        get_response = client.get(url, headers=admin_headers)
        assert get_response.status_code == 404  # not found!


@pytest.mark.skip(reason="doesn't play nicely with other resource tests")
@pytest.mark.usefixtures("db_session")
class TestCitationsResource:
    @pytest.mark.parametrize(
        ["params", "data"],
        [
            (
                {
                    "review_id": 1,
                    "source_type": "database",
                    "source_name": "SOURCE_NAMEX",
                    "source_url": "http://www.example.com/SOURCEX",
                },
                {"title": "TITLEX", "abstract": "ABSTRACTX"},
            ),
        ],
    )
    def test_post(self, params, data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("citations_citations_resource", **params)
        response = client.post(url, json=data, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert {k: response_data[k] for k in data.keys()} == data
