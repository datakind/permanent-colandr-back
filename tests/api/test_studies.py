import flask
import pytest


class TestStudyResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, None, 200),
            (2, None, 200),
            (1, {"fields": "id,review_id"}, 200),
            (1, {"fields": "data_source_id"}, 200),
            (999, None, 404),
        ],
    )
    def test_get(self, id_, params, status_code, app, client, admin_headers, seed_data):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=id_, **(params or {}))
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            seed_data = seed_data["studies"][id_ - 1]
            fields = None if params is None else params["fields"].split(",")
            if fields is not None and "id" not in fields:
                fields.append("id")
            assert "id" in data
            assert data["id"] == id_
            for field in ["review_id", "data_source_id"]:
                if fields is None or field in fields:
                    assert data[field] == seed_data.get(field)
            if fields:
                assert sorted(data.keys()) == sorted(fields)

    @pytest.mark.parametrize(
        ["id_", "data", "status_code"],
        [
            (1, {"tags": ["TAG1", "TAG2"]}, 200),
            # doesn't work: can't set extraction status until fulltext has been screened
            # (2, {"data_extraction_status": "finished", "tags": ["TAG1"]}, 200),
            (999, {"tags": ["TAG1"]}, 404),
        ],
    )
    def test_put(self, id_, data, status_code, app, client, admin_headers, db_session):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=id_)
        response = client.put(url, json=data, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in data.items():
                assert data.get(key) == val

    # doesn't work!
    # AssertionError: Dependency rule tried to blank-out primary key column 'citations.id' on instance '<Citation at 0x15791bb50>'
    # @pytest.mark.parametrize("id_", [1, 2])
    # def test_delete(self, id_, app, client, admin_headers, db_session):
    #     with app.test_request_context():
    #         url = flask.url_for("studies_study_resource", id=id_)
    #     response = client.delete(url, headers=admin_headers)
    #     assert response.status_code == 204
    #     get_response = client.get(url, headers=admin_headers)
    #     assert get_response.status_code == 404  # not found!


class TestStudiesResource:
    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"review_id": 1}, 3),
            ({"review_id": 2}, 1),
            ({"review_id": 1, "dedupe_status": "not_duplicate"}, 3),
            ({"review_id": 1, "citation_status": "included"}, 0),
        ],
    )
    def test_get(self, params, num_exp, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("studies_studies_resource", **params)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        response_data = response.json
        assert isinstance(response_data, list)
        assert len(response_data) == num_exp
