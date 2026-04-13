import pytest

from colandr.api.v1 import authz

from .. import helpers
from ..fixtures.seed_ids import Reviews, Users


@pytest.mark.parametrize(
    ["current_user_id", "review_id", "params", "exp_result"],
    # TODO: try to add frozen review cases here
    [
        pytest.param(
            Users.ADMIN,
            Reviews.SHARED,
            None,
            True,
            id="admin_any_role_on_shared_review",
        ),
        pytest.param(
            Users.ADMIN,
            Reviews.OWNED,
            {"for_roles": ["owner"]},
            True,
            id="admin_owner_role_on_owned_review",
        ),
        pytest.param(
            Users.MEMBER,
            Reviews.SHARED,
            {"for_roles": ["owner", "member"]},
            True,
            id="member_owner_or_member_role_on_shared_review",
        ),
        pytest.param(
            Users.MEMBER,
            Reviews.SHARED,
            {"for_roles": ["owner"]},
            False,
            id="member_lacks_owner_role_on_shared_review",
        ),
        pytest.param(
            Users.OWNER,
            Reviews.FROZEN,
            None,
            False,
            id="owner_not_member_of_frozen_review",
        ),
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
        pytest.param(
            Users.ADMIN,
            Users.ADMIN,
            None,
            True,
            id="admin_self",
        ),
        pytest.param(
            Users.ADMIN,
            Users.OWNER,
            None,
            True,
            id="admin_other_user",
        ),
        pytest.param(
            Users.OWNER,
            Users.OWNER,
            None,
            True,
            id="non_admin_self",
        ),
        pytest.param(
            Users.ADMIN,
            Users.MEMBER,
            {"if_collaborator": False},
            True,
            id="admin_other_user_collaborator_check_disabled",
        ),
        pytest.param(
            Users.OWNER,
            Users.MEMBER,
            {"if_collaborator": True},
            True,
            id="collaborators_via_shared_review",
        ),
        pytest.param(
            Users.OWNER,
            Users.MEMBER,
            {"if_collaborator": False},
            False,
            id="non_collaborator_check_disabled_returns_false",
        ),
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
