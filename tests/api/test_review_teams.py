import flask
import pytest


class TestReviewTeamResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, None, 200),
            (2, None, 200),
            (1, {"fields": "id,name"}, 200),
            (1, {"fields": "name"}, 200),
            (999, None, 404),
        ],
    )
    def test_get(self, id_, params, status_code, app, client, admin_headers, seed_data):
        with app.test_request_context():
            url = flask.url_for(
                "review_teams_review_team_resource", id=id_, **(params or {})
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            seed_data = [
                record
                for record in seed_data["review_user_associations"]
                if record["review_id"] == id_
            ]
            exp_user_ids = sorted(set(record["user_id"] for record in seed_data))
            assert sorted(record["id"] for record in data) == exp_user_ids
            exp_is_owners = {
                record["user_id"]: record["user_role"] == "owner"
                for record in seed_data
            }
            assert {
                record["id"]: record["is_owner"] for record in data
            } == exp_is_owners
            fields = None if params is None else params["fields"].split(",")
            if fields is not None:
                for field in ["id", "is_owner"]:
                    if field not in fields:
                        fields.append(field)
            assert all("id" in record for record in data)
            if fields:
                assert all(sorted(record.keys()) == sorted(fields) for record in data)

    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, {"action": "make_owner", "user_id": 3}, 200),
            (1, {"action": "set_role", "user_id": 3, "user_role": "owner"}, 200),
            (1, {"action": "set_role", "user_id": 3, "user_role": "member"}, 200),
            (1, {"action": "set_role", "user_id": 4, "user_role": "member"}, 404),
            (1, {"action": "remove", "user_id": 3}, 200),
        ],
    )
    def test_put(
        self, id_, params, status_code, app, client, admin_headers, db_session
    ):
        with app.test_request_context():
            url = flask.url_for("review_teams_review_team_resource", id=id_, **params)
        response = client.put(url, json=params, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            if params["action"] == "make_owner":
                modified_user = [
                    record for record in data if record["id"] == params["user_id"]
                ][0]
                assert modified_user["is_owner"] is True
            elif params["action"] == "set_role":
                modified_user = [
                    record for record in data if record["id"] == params["user_id"]
                ][0]
                assert modified_user["is_owner"] is (params["user_role"] == "owner")
            elif params["action"] == "remove":
                assert not [
                    record for record in data if record["id"] == params["user_id"]
                ]
