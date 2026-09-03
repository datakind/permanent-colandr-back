import pytest


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
    def test_get(self, id_, params, api):
        response = api.get(FULLTEXT_UPLOAD_API_ENDPOINT, id=id_, **(params or {}))
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
    def test_post(self, id_, file_name, api, request):
        dir_path = request.config.rootpath
        file_path = dir_path / "tests" / "fixtures" / "fulltexts" / file_name
        files = {"uploaded_file": (open(file_path, mode="rb"), file_path)}
        response = api.post(FULLTEXT_UPLOAD_API_ENDPOINT, id=id_, files=files)
        assert response.status_code == 200
        data = response.json
        assert data
        assert data["id"] == id_

    @pytest.mark.parametrize("id_", [1])
    def test_delete(self, id_, api):
        response = api.delete(FULLTEXT_UPLOAD_API_ENDPOINT, id=id_)
        assert response.status_code == 204
