import flask
import pytest
import sqlalchemy as sa


@pytest.mark.usefixtures("db_session")
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
            (
                {
                    "review_id": 1,
                    "status": "included",
                    "source_type": "database",
                },
                "example.bib",
            ),
        ],
    )
    def test_post(
        self, params, file_name, app, client, db_session, admin_headers, request
    ):
        # NOTE: we specify user ids in the seed data, but apparently the auto-increment
        # sequence isn't made aware of it; so, we need to manually bump the start value
        # so that this created user isn't assigned id=1, which is already in use
        # and so violates a unique constraint. seems crazy, but here we are
        db_session.execute(sa.text("ALTER SEQUENCE studies_id_seq RESTART WITH 5"))
        with app.test_request_context():
            url = flask.url_for(
                "citation_imports_citations_imports_resource", **(params or {})
            )
        dir_path = request.config.rootpath
        file_path = dir_path / "tests" / "fixtures" / "citations" / file_name
        files = {"uploaded_file": (open(file_path, mode="rb"), file_path)}
        response = client.post(url, data=files, headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"review_id": 1}, 2),
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
