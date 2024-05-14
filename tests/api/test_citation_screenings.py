import flask
import pytest

from colandr.apis import auth

from .. import helpers


# TODO: figure out why cli seed command errors when screening records have "id" fields


@pytest.mark.usefixtures("db_session")
class TestCitationScreeningsResource:
    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "params", "exp_data"],
        [
            (
                1,
                1,
                None,
                [
                    {
                        "user_id": 2,
                        "review_id": 1,
                        "citation_id": 1,
                        "status": "included",
                    }
                ],
            ),
            (
                2,
                4,
                None,
                [
                    {
                        "user_id": 2,
                        "review_id": 2,
                        "citation_id": 4,
                        "status": "included",
                    },
                    {
                        "user_id": 3,
                        "review_id": 2,
                        "citation_id": 4,
                        "status": "included",
                    },
                ],
            ),
            (
                3,
                3,
                {"fields": "id,review_id,citation_id"},
                [{"review_id": 1, "citation_id": 3}],
            ),
        ],
    )
    def test_get(
        self, current_user_id, study_id, params, exp_data, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource",
                id=study_id,
                **(params or {}),
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.get(url, headers=headers)
        assert response.status_code == 200
        data = response.json
        assert isinstance(data, list)
        for item, exp_item in zip(data, exp_data):
            assert "id" in item
            assert {k: v for k, v in item.items() if k in exp_item} == exp_item

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
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource",
                id=study_id,
                **(params or {}),
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.get(
                    url, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "data"],
        [
            (1, 3, {"user_id": 2, "status": "included"}),
            (
                2,
                1,
                {"user_id": 2, "status": "excluded", "exclude_reasons": ["REASON3"]},
            ),
        ],
    )
    def test_put(self, current_user_id, study_id, data, app, client, db_session):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=study_id
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.put(url, json=data, headers=headers)
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == study_id
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "data", "status_code"],
        [
            (1, 1, {"user_id": 2}, 422),
            (1, 1, {"user_id": 2, "status": "excluded"}, 400),
            (1, 999, {"user_id": 1, "status": "included"}, 404),
        ],
    )
    def test_put_errors(
        self, current_user_id, study_id, data, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=study_id
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                response = client.put(
                    url, json=data, headers=auth.pack_header_for_user(current_user)
                )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "study_id"],
        [
            (2, 1),
            (3, 4),
        ],
    )
    def test_delete(self, current_user_id, study_id, app, client, db_session):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=study_id
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.delete(url, headers=headers)
                assert response.status_code == 204
                assert not any(
                    item["user_id"] == current_user_id
                    for item in client.get(url, headers=headers).json
                )  # not found!

    @pytest.mark.parametrize(
        ["current_user_id", "study_id", "status_code"],
        [
            (1, 999, 404),  # only existing screenings can be deleted
            (4, 1, 403),  # only reviewers can delete their own screenings
        ],
    )
    def test_delete_errors(
        self, current_user_id, study_id, status_code, app, client, db_session
    ):
        with app.test_request_context():
            url = flask.url_for(
                "citation_screenings_citation_screenings_resource", id=study_id
            )
        with app.app_context():
            with helpers.set_current_user(current_user_id, db_session) as current_user:
                headers = auth.pack_header_for_user(current_user)
                response = client.delete(url, headers=headers)
                assert response.status_code == status_code

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
            ({"user_id": 2}, 4),
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
