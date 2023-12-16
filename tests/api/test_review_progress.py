import flask
import pytest


@pytest.mark.usefixtures("db_session")
class TestReviewProgressResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, {}, 200),
            (1, {"step": "planning"}, 200),
            (2, {}, 200),
            (1, {"user_view": True}, 200),
            (999, {}, 404),
        ],
    )
    def test_get(self, id_, params, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "review_progress_review_progress_resource", id=id_, **params
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert data
            assert isinstance(data, dict)
            if "step" in params and params["step"] != "all":
                assert len(data) == 1
                assert params["step"] in data
            else:
                assert len(data) == 4
                assert all(
                    step in data
                    for step in [
                        "planning",
                        "citation_screening",
                        "fulltext_screening",
                        "data_extraction",
                    ]
                )

    @pytest.mark.parametrize(
        ["id_", "exp_data"],
        [
            (
                1,
                {
                    "planning": {
                        "objective": True,
                        "research_questions": True,
                        "pico": True,
                        "keyterms": True,
                        "selection_criteria": True,
                        "data_extraction_form": True,
                    },
                    "citation_screening": {
                        "not_screened": 0,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 2,
                        "excluded": 1,
                    },
                    "fulltext_screening": {
                        "not_screened": 0,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 1,
                        "excluded": 1,
                    },
                    "data_extraction": {"not_started": 1, "started": 0, "finished": 0},
                },
            ),
            (
                2,
                {
                    "planning": {
                        "objective": False,
                        "research_questions": False,
                        "pico": False,
                        "keyterms": False,
                        "selection_criteria": False,
                        "data_extraction_form": False,
                    },
                    "citation_screening": {
                        "not_screened": 0,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 1,
                        "excluded": 0,
                    },
                    "fulltext_screening": {
                        "not_screened": 1,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 0,
                        "excluded": 0,
                    },
                    "data_extraction": {"not_started": 0, "started": 0, "finished": 0},
                },
            ),
        ],
    )
    def test_exp_result(self, id_, exp_data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("review_progress_review_progress_resource", id=id_)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data == exp_data
