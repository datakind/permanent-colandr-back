import pytest


FULLTEXT_SCREENING_API_ENDPOINT = "fulltext_screenings.fulltext_screening"
FULLTEXT_SCREENINGS_API_ENDPOINT = "fulltext_screenings.fulltext_screenings"


@pytest.mark.usefixtures("db_session")
class TestFulltextScreeningAPI:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code", "num_exp"],
        [
            (1, None, 200, 2),
            (2, None, 200, 1),
            (1, {"fields": "id,review_id"}, 200, 2),
            (1, {"fields": "fulltext_id,status"}, 200, 2),
            (999, None, 404, 0),
        ],
    )
    def test_get(self, id_, params, status_code, num_exp, api):
        response = api.get(FULLTEXT_SCREENING_API_ENDPOINT, id=id_, **(params or {}))
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            records = response.json
            fields = None if params is None else params["fields"].split(",")
            if fields and "id" not in fields:
                fields.append("id")
            assert isinstance(records, list) and len(records) == num_exp
            for record in records:
                if "fulltext_id" in record:
                    assert record["fulltext_id"] == id_
                if fields:
                    assert "id" in record
                    assert sorted(record.keys()) == sorted(fields)

    @pytest.mark.parametrize(
        ["id_", "data", "status_code"],
        [
            (2, {"user_id": 2, "status": "included"}, 200),
            (
                1,
                {
                    "user_id": 3,
                    "status": "excluded",
                    "exclude_reasons": ["REASON3"],
                },
                200,
            ),
            (999, {"status": "included"}, 422),
        ],
    )
    def test_put(self, id_, data, status_code, api):
        response = api.put(FULLTEXT_SCREENING_API_ENDPOINT, id=id_, json=data)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in data.items():
                assert data.get(key) == val

    @pytest.mark.parametrize("id_", [1, 2])
    def test_delete(self, id_, api):
        response = api.delete(FULLTEXT_SCREENING_API_ENDPOINT, id=id_)
        # NOTE: this operation is currently only allowed for the screener themself
        assert response.status_code == 403
        # get_response = client.get(url, headers=admin_headers)
        # assert get_response.status_code == 404  # not found!

    @pytest.mark.parametrize(
        ["fulltext_id", "data", "status_code"],
        [
            (2, {"user_id": 3, "review_id": 1, "status": "included"}, 200),
            (999, {"status": "included"}, 404),
        ],
    )
    def test_post(self, fulltext_id, data, status_code, api):
        response = api.post(FULLTEXT_SCREENING_API_ENDPOINT, id=fulltext_id, json=data)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in data.items():
                assert data.get(key) == val


@pytest.mark.usefixtures("db_session")
class TestFulltextScreeningsAPI:
    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"fulltext_id": 2}, 1),
            ({"user_id": 2}, 2),
            ({"review_id": 1}, 3),
            ({"review_id": 1, "user_id": 3}, 1),
        ],
    )
    def test_get(self, params, num_exp, api):
        response = api.get(FULLTEXT_SCREENINGS_API_ENDPOINT, **params)
        assert response.status_code == 200
        response_data = response.json
        assert isinstance(response_data, list)
        assert len(response_data) == num_exp
