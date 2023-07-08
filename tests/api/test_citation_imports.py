import flask
import pytest


class TestCitationsImportsResource:
    @pytest.mark.parametrize(
        ["params", "file_name"],
        [
            (
                {
                    "review_id": 1,
                    "status": "included",
                    "source_type": "database",
                },
                "example.ris",
            ),
        ],
    )
    def test_post(self, params, file_name, app, client, admin_headers, request):
        with app.test_request_context():
            url = flask.url_for(
                "citation_imports_citations_imports_resource", **(params or {})
            )
        dir_path = request.config.rootpath
        file_path = dir_path / "tests" / "fixtures" / file_name
        files = {"uploaded_file": (open(file_path, mode="rb"), file_path)}
        response = client.post(url, data=files, headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"review_id": 1}, 1),
        ],
    )
    def test_get(self, params, num_exp, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "citation_imports_citations_imports_resource", **(params or {})
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert isinstance(data, list) and len(data) == num_exp