import flask
import pytest


@pytest.mark.usefixtures("db_session")
class TestCitationScreeningsResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code", "num_exp"],
        [
            (1, None, 200, 1),
            (4, None, 200, 2),
            (1, {"fields": "id,review_id"}, 200, 1),
            (1, {"fields": "status"}, 200, 1),
            (999, None, 404, 0),
        ],
    )
    def test_get(
        self, id_, params, status_code, num_exp, app, client, admin_headers, seed_data
    ):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource",
                id=id_,
                **(params or {}),
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            records = response.json
            seed_data = seed_data["citation_screenings"][id_ - 1]
            fields = None if params is None else params["fields"].split(",")
            # if fields is not None and "id" not in fields:
            #     fields.append("id")
            assert isinstance(records, list) and len(records) == num_exp
            for record in records:
                # TODO: figure out what to do with these checks below
                # assert "id" in record
                # assert record["citation_id"] == id_
                for field in ["citation_id", "review_id", "status"]:
                    if fields is None or field in fields:
                        assert record[field] == seed_data.get(field)
                if fields:
                    assert sorted(record.keys()) == sorted(fields)

    @pytest.mark.parametrize(
        ["id_", "data", "status_code"],
        [
            (3, {"user_id": 2, "status": "included"}, 200),
            (
                4,
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
    def test_put(self, id_, data, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=id_
            )
        response = client.put(url, json=data, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in data.items():
                assert data.get(key) == val

    @pytest.mark.parametrize("id_", [1, 2])
    def test_delete(self, id_, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=id_
            )
        response = client.delete(url, headers=admin_headers)
        # NOTE: this operation is currently only allowed for the screener themself
        assert response.status_code == 403
        # get_response = client.get(url, headers=admin_headers)
        # assert get_response.status_code == 404  # not found!

    @pytest.mark.parametrize(
        ["citation_id", "data", "status_code"],
        [
            (1, {"user_id": 3, "review_id": 1, "status": "included"}, 200),
            (
                3,
                {
                    "user_id": 3,
                    "status": "excluded",
                    "exclude_reasons": ["REASON3"],
                },
                200,
            ),
            (999, {"status": "included"}, 404),
        ],
    )
    def test_post(self, citation_id, data, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=citation_id
            )
        response = client.post(url, json=data, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in data.items():
                assert data.get(key) == val


@pytest.mark.usefixtures("db_session")
class TestCitationsScreeningsResource:
    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"citation_id": 1}, 1),
            ({"user_id": 2}, 3),
            ({"review_id": 2}, 2),
            ({"review_id": 2, "user_id": 3}, 1),
        ],
    )
    def test_get(self, params, num_exp, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citations_screenings_resource", **params
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert isinstance(response_data, list)
        assert len(response_data) == num_exp

    @pytest.mark.parametrize(
        ["params", "exp_data"],
        [
            ({"review_id": 1, "status_counts": True}, {"excluded": 1, "included": 2}),
            ({"review_id": 2, "status_counts": True}, {"included": 2}),
            ({"user_id": 3, "status_counts": True}, {"included": 1}),
            (
                {"user_id": 2, "review_id": 1, "status_counts": True},
                {"excluded": 1, "included": 2},
            ),
        ],
    )
    def test_get_status_counts(self, params, exp_data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citations_screenings_resource", **params
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert response_data and isinstance(response_data, dict)
        assert response_data == exp_data
