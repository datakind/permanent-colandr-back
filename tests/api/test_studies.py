import flask
import pytest

from colandr.apis import auth

from .. import helpers


@pytest.mark.usefixtures("db_session")
class TestStudyResource:
    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "params", "exp_data"],
        [
            (
                1,
                1,
                None,
                {"user_id": 2, "review_id": 1, "data_source_id": 1, "tags": ["TAG1"]},
            ),
            (
                2,
                2,
                None,
                {
                    "user_id": 2,
                    "review_id": 1,
                    "data_source_id": 1,
                    "tags": ["TAG3", "TAG2", "TAG1"],
                },
            ),
            (
                1,
                1,
                {"fields": "id,user_id,review_id"},
                {"user_id": 2, "review_id": 1},
            ),
            (3, 1, {"fields": "data_source_id"}, {"data_source_id": 1}),
        ],
    )
    def test_get(
        self, current_user_id, study_id, params, exp_data, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=study_id, **(params or {}))
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.get(url, headers=headers)
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == study_id
        assert {k: v for k, v in data.items() if k in exp_data} == exp_data

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "params", "status_code"],
        [
            (1, 999, None, 404),
            (4, 1, None, 403),
        ],
    )
    def test_get_errors(
        self, current_user_id, study_id, params, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=study_id, **(params or {}))
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.get(
                    url, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "data"],
        [
            (1, 1, {"tags": ["TAG1", "TAG2"]}),
            (2, 1, {"tags": ["THIS-IS-A-REALLLLLLLLLLLLLLLLLLLLLLLLLLY-LONG-TAG1"]}),
        ],
    )
    def test_put(self, current_user_id, study_id, data, app, client, db_session):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=study_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.put(
                    url, json=data, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == study_id
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "data", "status_code"],
        [
            (4, 1, {"tags": ["NEW_TAG1"]}, 403),
            (2, 1, {"tags": ["X" * 65]}, 422),
            (2, 2, {"data_extraction_status": "finished"}, 403),
            (1, 999, {"tags": ["NEW_TAG1"]}, 404),
        ],
    )
    def test_put_errors(
        self, current_user_id, study_id, data, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=study_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.put(
                    url, json=data, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "study_id"],
        [
            (1, 1),
            (2, 2),
        ],
    )
    def test_delete(self, current_user_id, study_id, app, client, db_session):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=study_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.delete(url, headers=headers)
                assert response.status_code == 204
                assert client.get(url, headers=headers).status_code == 404  # not found!

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "status_code"],
        [
            (1, 999, 404),  # only existing studies can be deleted
            (4, 1, 403),  # only admins and review members can delete reviews
        ],
    )
    def test_delete_errors(
        self, current_user_id, study_id, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("studies_study_resource", id=study_id)
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.delete(url, headers=headers)
                assert response.status_code == status_code


@pytest.mark.usefixtures("db_session")
class TestStudiesResource:
    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"review_id": 1}, 3),
            ({"review_id": 2}, 1),
            ({"review_id": 1, "dedupe_status": "not_duplicate"}, 3),
            ({"review_id": 1, "citation_status": "included"}, 2),
            # TODO: add a proper test for citation ranking model ordering
            ({"review_id": 1, "order_by": "relevance"}, 3),
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
