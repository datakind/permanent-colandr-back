import flask
import pytest


@pytest.mark.usefixtures("db_session")
class TestStudyTagsResource:
    @pytest.mark.parametrize(
        ["params", "status_code", "exp_result"],
        [
            ({"review_id": 1}, 200, ["TAG1", "TAG2", "TAG3"]),
            ({"review_id": 2}, 200, ["TAG4"]),
            ({"review_id": 999}, 404, None),
        ],
    )
    def test_get(self, params, status_code, exp_result, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("study_tags_study_tags_resource", **params)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert isinstance(data, list)
            assert data == exp_result
