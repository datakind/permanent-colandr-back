import pytest


FULLTEXT_API_ENDPOINT = "fulltexts.fulltext"


@pytest.mark.usefixtures("db_session")
class TestFulltextAPI:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, None, 200),
            (2, None, 200),
            (1, {"fields": "id,review_id"}, 200),
            (1, {"fields": "filename"}, 200),
            (999, None, 404),
        ],
    )
    def test_get(self, id_, params, status_code, api):
        response = api.get(FULLTEXT_API_ENDPOINT, id=id_, **(params or {}))
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            fields = None if params is None else params["fields"].split(",")
            if fields is not None and "id" not in fields:
                fields.append("id")
            assert "id" in data
            assert data["id"] == id_
            if fields:
                assert sorted(data.keys()) == sorted(fields)

    @pytest.mark.parametrize("id_", [1, 2])
    def test_delete(self, id_, api):
        response = api.delete(FULLTEXT_API_ENDPOINT, id=id_)
        assert response.status_code == 204
        # TODO: decide on delete behavior for study.fulltext
        # get_response = client.get(url, headers=admin_headers)
        # assert get_response.status_code == 404  # not found!
        get_response = api.get(FULLTEXT_API_ENDPOINT, id=id_)
        assert get_response.json == {}  # empty!
