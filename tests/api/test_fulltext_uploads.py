import flask
import pytest


# app v1
# FULLTEXT_UPLOAD_API_ENDPOINT = "fulltext_uploads_fulltext_upload_resource"
# app v1.1
FULLTEXT_UPLOAD_API_ENDPOINT = "fulltext_uploads.fulltext_upload"


@pytest.mark.usefixtures("db_session")
class TestFulltextUploadAPI:
    @pytest.mark.parametrize(
        ["id_", "params"],
        [
            (1, {"review_id": 1}),
            # NOTE: review_id is now required, unless we decide to change that
            # (1, {}),
        ],
    )
    def test_get(self, id_, params, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(FULLTEXT_UPLOAD_API_ENDPOINT, id=id_, **(params or {}))
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        # TODO: figure out if/how we can make send_from_directory() work correctly in test
        # data = response.json
        # assert data

    @pytest.mark.parametrize(
        ["id_", "file_name"],
        [
            (4, "example-journal-short.pdf"),
            (2, "example-journal.pdf"),
        ],
    )
    def test_post(self, id_, file_name, app, client, admin_headers, request):
        with app.test_request_context():
            url = flask.url_for(FULLTEXT_UPLOAD_API_ENDPOINT, id=id_)
        dir_path = request.config.rootpath
        file_path = dir_path / "tests" / "fixtures" / "fulltexts" / file_name
        files = {"uploaded_file": (open(file_path, mode="rb"), file_path)}
        response = client.post(url, data=files, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert data["id"] == id_

    @pytest.mark.parametrize("id_", [1])
    def test_delete(self, id_, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(FULLTEXT_UPLOAD_API_ENDPOINT, id=id_)
        response = client.delete(url, headers=admin_headers)
        assert response.status_code == 204
