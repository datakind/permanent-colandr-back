import flask
import pytest


USER_API_ENDPOINT = "users.user"
USERS_API_ENDPOINT = "users.users"


def test_api_path(api):
    response = api.get(USER_API_ENDPOINT, id=1)
    assert response.status_code == 200


@pytest.mark.usefixtures("db_session")
class TestUserAPI:
    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "params", "exp_data"],
        [
            (
                1,
                1,
                None,
                {
                    "name": "NAME1",
                    "email": "name1@example.com",
                    "is_confirmed": True,
                    "is_admin": True,
                },
            ),
            (
                1,
                2,
                None,
                {
                    "name": "NAME2",
                    "email": "name2@example.com",
                    "is_confirmed": True,
                    "is_admin": False,
                },
            ),
            (
                2,
                3,
                None,
                {
                    "name": "NAME3",
                    "email": "name3@example.com",
                    "is_confirmed": True,
                    "is_admin": False,
                },
            ),
            (
                1,
                1,
                {"fields": "id,name,email"},
                {"name": "NAME1", "email": "name1@example.com"},
            ),
            (
                2,
                2,
                {"fields": "name,email"},
                {"name": "NAME2", "email": "name2@example.com"},
            ),
        ],
    )
    def test_get(self, current_user_id, user_id, params, exp_data, api):
        response = api.as_user(current_user_id).get(
            USER_API_ENDPOINT, id=user_id, **(params or {})
        )
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == user_id
        assert "password" not in data
        assert {k: v for k, v in data.items() if k in exp_data} == exp_data

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "params", "status_code"],
        [
            (1, 999, None, 404),
            (4, 1, None, 403),
        ],
    )
    def test_get_errors(self, current_user_id, user_id, params, status_code, api):
        response = api.as_user(current_user_id).get(
            USER_API_ENDPOINT, id=user_id, **(params or {})
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "user_id"],
        [
            (1, 2),
            (3, 3),
        ],
    )
    def test_delete(self, current_user_id, user_id, api, admin_headers, client):
        del_response = api.as_user(current_user_id).delete(
            USER_API_ENDPOINT, id=user_id
        )
        assert del_response.status_code == 204
        # verify as admin using raw fixtures (api is still in user mode)
        with client.application.test_request_context():
            url = flask.url_for(USER_API_ENDPOINT, id=user_id)
        assert client.get(url, headers=admin_headers).status_code == 404  # not found!

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "status_code"],
        [
            (1, 999, 404),
            (2, 3, 403),
        ],
    )
    def test_delete_errors(self, current_user_id, user_id, status_code, api):
        response = api.as_user(current_user_id).delete(USER_API_ENDPOINT, id=user_id)
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "data"],
        [
            (1, 2, {"name": "NEW_NAME2"}),
            (1, 3, {"email": "name3@example.net"}),
            (1, 4, {"name": "NEW_NAME4", "email": "name4@example.net"}),
            (1, 2, {"is_admin": True}),
        ],
    )
    def test_put(self, current_user_id, user_id, data, api):
        response = api.as_user(current_user_id).put(
            USER_API_ENDPOINT, id=user_id, json=data
        )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == user_id
        assert "password" not in obs_data
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["current_user_id", "user_id", "data", "status_code"],
        [
            (3, 2, {"name": "NEW_NAME2"}, 403),
            (1, 999, {"name": "NEW_NAME999"}, 404),
            (2, 2, {"is_admin": True}, 403),
            # TODO: figure out if there's a way to throw nice errors
            # in case "current user" doesn't actually exist
            # (999, 999, {"name": "NEW_NAME999"}, 404),
        ],
    )
    def test_put_errors(self, current_user_id, user_id, data, status_code, api):
        response = api.as_user(current_user_id).put(
            USER_API_ENDPOINT, id=user_id, json=data
        )
        assert response.status_code == status_code


@pytest.mark.usefixtures("db_session")
class TestUsersAPI:
    @pytest.mark.parametrize(
        ["email", "review_id", "admins", "user_ids"],
        [
            ("name1@example.com", None, None, 1),
            ("name2@example.com", 1, None, 2),
            (None, 1, None, [1, 2, 3]),
            (None, None, True, [1]),
        ],
    )
    def test_get(self, email, review_id, admins, user_ids, api):
        response = api.get(
            USERS_API_ENDPOINT, email=email, review_id=review_id, admins=admins
        )
        assert response.status_code == 200
        data = response.json
        assert data
        assert isinstance(data, list)
        if email is not None:
            assert len(data) == 1
            assert data[0]["id"] == user_ids
            assert data[0]["email"] == email
        elif review_id is not None:
            assert [user["id"] for user in data] == user_ids
        elif admins is not None:
            assert isinstance(data, list)
            assert [user["id"] for user in data] == user_ids

    @pytest.mark.parametrize(
        ["current_user_id", "email", "review_id", "admins", "status_code"],
        [
            (1, "name999@example.com", None, None, 404),
            (1, None, 999, None, 404),
            (4, None, 1, None, 403),
            (2, None, None, True, 403),
        ],
    )
    def test_get_errors(
        self,
        current_user_id,
        email,
        review_id,
        admins,
        status_code,
        api,
    ):
        response = api.as_user(current_user_id).get(
            USERS_API_ENDPOINT, email=email, review_id=review_id, admins=admins
        )
        assert response.status_code == status_code
