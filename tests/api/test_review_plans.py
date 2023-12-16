import flask
import pytest


@pytest.mark.usefixtures("db_session")
class TestReviewPlanResource:
    @pytest.mark.parametrize(
        ["id", "params", "status_code"],
        [
            (1, None, 200),
            (1, {"fields": "id,objective"}, 200),
            (1, {"fields": "pico"}, 200),
        ],
    )
    def test_get(self, id, params, status_code, app, client, admin_headers, seed_data):
        with app.test_request_context():
            url = flask.url_for(
                "review_plans_review_plan_resource", id=id, **(params or {})
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            seed_data = seed_data["review_plans"][id - 1]
            fields = None if params is None else params["fields"].split(",")
            if fields is not None and "id" not in fields:
                fields.append("id")
            assert "id" in data
            assert data["id"] == id
            for field in ["objective", "pico"]:
                if fields is None or field in fields:
                    assert data[field] == seed_data.get(field)
            if fields:
                assert sorted(data.keys()) == sorted(fields)

    @pytest.mark.parametrize(
        ["id", "data", "status_code"],
        [
            (1, {"objective": "NEW_OBJECTIVE1"}, 200),
            (1, {"research_questions": ["NEW_Q1", "NEW_Q2"]}, 200),
            (
                1,
                {
                    "keyterms": [
                        {"group": "GROUP1", "term": "TERM1", "synonyms": ["SYN1"]},
                        {"group": "GROUP1", "term": "TERM2"},
                    ]
                },
                200,
            ),
            (999, {"objective": "NEW_OBJECTIVE999"}, 404),
        ],
    )
    def test_put(self, id, data, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("review_plans_review_plan_resource", id=id)
        response = client.put(url, json=data, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            for key, val in data.items():
                assert data.get(key) == val

    @pytest.mark.parametrize("id", [1])
    def test_delete(self, id, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("review_plans_review_plan_resource", id=id)
        response = client.delete(url, headers=admin_headers)
        assert response.status_code == 204
        get_response = client.get(url, headers=admin_headers)
        get_data = get_response.json
        # "deleted" review plan is just emptied out
        for key in [
            "objective",
            "research_questions",
            "pico",
            "keyterms",
            "selection_criteria",
            "data_extraction_form",
        ]:
            assert not get_data[key]
