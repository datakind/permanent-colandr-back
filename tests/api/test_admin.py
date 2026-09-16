import pytest
import sqlalchemy as sa


GET_REVIEWS_API_ENDPOINT = "admin.get_reviews"
POST_USERS_API_ENDPOINT = "admin.post_users"


@pytest.mark.usefixtures("db_session")
class TestGetReviewsAPI:
    @pytest.mark.parametrize(
        ["review_ids", "num_exp"],
        [("1", 1), ("1,2", 2), ("1,2,99", 2)],
    )
    def test_get(self, review_ids, num_exp, api):
        response = api.get(GET_REVIEWS_API_ENDPOINT, review_ids=review_ids)
        assert response.status_code == 200
        data = response.json
        assert data
        assert len(data) == num_exp


@pytest.mark.usefixtures("db_session")
class TestPostUsersAPI:
    @pytest.mark.parametrize(
        "data",
        [
            {
                "name": "NAMEX",
                "email": "namex@example.net",
                "password": "PASSWORDX",
            },
        ],
    )
    def test_post(self, data, api, db_session):
        # NOTE: we specify user ids in the seed data, but apparently the auto-increment
        # sequence isn't made aware of it; so, we need to manually bump the start value
        # so that this created user isn't assigned id=1, which is already in use
        # and so violates a unique constraint. seems crazy, but here we are
        db_session.execute(sa.text("ALTER SEQUENCE users_id_seq RESTART WITH 6"))
        response = api.post(POST_USERS_API_ENDPOINT, json=data)
        assert response.status_code == 200
        response_data = response.json
        assert data["email"] == response_data["email"]

    @pytest.mark.parametrize(
        ["current_user_id", "data", "status_code"],
        [
            (1, {"name": "NAMEX", "email": "namex@example.net"}, 422),
            (1, {"email": "namex@example.net", "password": "PASSWORDX"}, 422),
            (1, {"name": "NAMEX", "password": "PASSWORDX"}, 422),
            (
                2,
                {
                    "name": "NAMEX",
                    "email": "namex@example.net",
                    "password": "PASSWORDX",
                },
                422,
            ),
        ],
    )
    def test_post_errors(self, current_user_id, data, status_code, api):
        response = api.as_user(current_user_id).post(POST_USERS_API_ENDPOINT, data=data)
        assert response.status_code == status_code
