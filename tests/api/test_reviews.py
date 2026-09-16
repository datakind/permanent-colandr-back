import flask
import pytest
import sqlalchemy as sa


REVIEW_API_ENDPOINT = "reviews.review"
REVIEWS_API_ENDPOINT = "reviews.reviews"


@pytest.mark.usefixtures("db_session")
class TestReviewAPI:
    @pytest.mark.parametrize(
        ["current_user_id", "review_id", "params", "exp_data"],
        [
            (1, 1, None, {"name": "NAME1", "description": "DESCRIPTION1"}),
            (
                1,
                2,
                None,
                {
                    "name": "NAME2",
                    "description": "DESCRIPTION2",
                    "num_citation_screening_reviewers": 1,
                    "num_fulltext_screening_reviewers": 2,
                },
            ),
            (3, 1, None, {"name": "NAME1", "description": "DESCRIPTION1"}),
            (1, 1, {"fields": "id,name"}, {"name": "NAME1"}),
            (1, 1, {"fields": "description"}, {"description": "DESCRIPTION1"}),
        ],
    )
    def test_get(self, current_user_id, review_id, params, exp_data, api):
        response = api.as_user(current_user_id).get(
            REVIEW_API_ENDPOINT, id=review_id, **(params or {})
        )
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == review_id
        assert {k: v for k, v in data.items() if k in exp_data} == exp_data

    @pytest.mark.parametrize(
        ["current_user_id", "review_id", "params", "status_code"],
        [
            (1, 999, None, 404),
            (2, 3, None, 403),
        ],
    )
    def test_get_errors(self, current_user_id, review_id, params, status_code, api):
        response = api.as_user(current_user_id).get(
            REVIEW_API_ENDPOINT, id=review_id, **(params or {})
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "review_id", "data"],
        [
            (1, 1, {"name": "NEW_REVIEW_NAME1"}),
            (2, 1, {"description": "NEW_DESCRIPTION1"}),
            (1, 2, {"name": "NEW_REVIEW_NAME2", "description": "NEW_DESCRIPTION2"}),
            (1, 2, {"num_citation_screening_reviewers": 2}),
            (1, 2, {"num_fulltext_screening_reviewers": 3}),
        ],
    )
    def test_put(self, current_user_id, review_id, data, api):
        response = api.as_user(current_user_id).put(
            REVIEW_API_ENDPOINT, id=review_id, json=data
        )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == review_id
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["current_user_id", "review_id", "data", "status_code"],
        [
            (3, 1, {"name": "NEW_NAME1"}, 403),
            (1, 999, {"name": "NEW_NAME999"}, 404),
        ],
    )
    def test_put_errors(self, current_user_id, review_id, data, status_code, api):
        response = api.as_user(current_user_id).put(
            REVIEW_API_ENDPOINT, id=review_id, json=data
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "review_id"],
        [
            (1, 1),
            (2, 2),
        ],
    )
    def test_delete(self, current_user_id, review_id, api, admin_headers, client):
        del_response = api.as_user(current_user_id).delete(
            REVIEW_API_ENDPOINT, id=review_id
        )
        assert del_response.status_code == 204
        # hack: verify as admin using raw fixtures (since api is still in user mode)
        with client.application.test_request_context():
            url = flask.url_for(REVIEW_API_ENDPOINT, id=review_id)
        assert client.get(url, headers=admin_headers).status_code == 404

    @pytest.mark.parametrize(
        ["current_user_id", "review_id", "status_code"],
        [
            (1, 999, 404),  # only existing reviews can be deleted
            (3, 1, 403),  # only admins and owners can delete reviews
        ],
    )
    def test_delete_errors(self, current_user_id, review_id, status_code, api):
        response = api.as_user(current_user_id).delete(
            REVIEW_API_ENDPOINT, id=review_id
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        "data",
        [
            {"name": "NAMEX"},
            {"name": "NAMEX", "description": "DESCX"},
            {
                "name": "NAMEX",
                "num_citation_screening_reviewers": 2,
                "num_fulltext_screening_reviewers": 2,
            },
        ],
    )
    def test_post(self, data, api, db_session):
        # NOTE: we specify ids in the seed data, but apparently the auto-increment
        # sequence isn't made aware of it; so, we need to manually bump the start value
        # so that the created record isn't assigned id=1, which is already in use
        # and so violates a unique constraint
        db_session.execute(sa.text("ALTER SEQUENCE reviews_id_seq RESTART WITH 4"))
        response = api.post(REVIEWS_API_ENDPOINT, json=data)
        assert response.status_code == 200
        response_data = response.json
        assert data["name"] == response_data["name"]

    @pytest.mark.parametrize(
        ["current_user_id", "data", "status_code"],
        [
            (1, {"name": None, "description": "DESCX"}, 422),
            (1, {"name": "NAMEX", "foo": "bar"}, 422),
        ],
    )
    def test_post_errors(self, current_user_id, data, status_code, api):
        response = api.as_user(current_user_id).post(REVIEWS_API_ENDPOINT, json=data)
        assert response.status_code == status_code
