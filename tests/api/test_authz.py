import pytest

from colandr.api.v1 import authz

from .. import helpers


@pytest.mark.parametrize(
    ["current_user_id", "review_id", "params", "exp_result"],
    # TODO: try to add frozen review cases here
    [
        (1, 1, None, True),
        (1, 2, {"for_roles": ["owner"]}, True),
        (3, 1, {"for_roles": ["owner", "member"]}, True),
        (3, 1, {"for_roles": ["owner"]}, False),
        (2, 3, None, False),
    ],
)
def test_user_is_allowed_for_review(
    current_user_id, review_id, params, exp_result, app, db_session
):
    with app.app_context():
        with helpers.set_current_user(current_user_id, db_session) as current_user:
            assert current_user is not None  # type guard
            obs_result = authz.user_is_allowed_for_review(
                current_user, review_id, **(params or {})
            )
    assert obs_result == exp_result


@pytest.mark.parametrize(
    ["current_user_id", "user_id", "params", "exp_result"],
    [
        (1, 1, None, True),  # self && admin
        (1, 2, None, True),  # admin
        (2, 2, None, True),  # self
        (1, 3, {"if_collaborator": False}, True),  # admin &! collaborator
        (2, 3, {"if_collaborator": True}, True),  # collaborator
        (2, 3, {"if_collaborator": False}, False),  # != collaborator
    ],
)
def test_user_is_allowed_for_user(
    current_user_id, user_id, params, exp_result, app, db_session
):
    with app.app_context():
        with helpers.set_current_user(current_user_id, db_session) as current_user:
            assert current_user is not None  # type guard
            obs_result = authz.user_is_allowed_for_user(
                current_user, user_id, **(params or {})
            )
    assert obs_result == exp_result
