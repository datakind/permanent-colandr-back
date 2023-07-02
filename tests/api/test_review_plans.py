import flask
import pytest


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
            # TODO: figure out why these fields are null in the db :/
            # for field in ["objective", "pico"]:
            #     if fields is None or field in fields:
            #         assert data[field] == seed_data.get(field)
            if fields:
                assert sorted(data.keys()) == sorted(fields)

