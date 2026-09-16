"""Test authz role-graph."""

import pytest

from colandr.api.v1 import authz

from .. import factories, helpers


pytestmark = pytest.mark.usefixtures("db_empty")


def test_user_is_allowed_for_review(app, db_session):
    admin = factories.create_user(db_session, is_admin=True)
    owner = factories.create_user(db_session)
    member = factories.create_user(db_session)
    outsider = factories.create_user(db_session)
    review = factories.create_review_with_team(
        db_session, owner=owner, members=[member]
    )

    with app.app_context():
        with helpers.set_current_user(admin.id, db_session) as user:
            assert authz.user_is_allowed_for_review(user, review.id) is True
        with helpers.set_current_user(owner.id, db_session) as user:
            assert authz.user_is_allowed_for_review(user, review.id) is True
        with helpers.set_current_user(member.id, db_session) as user:
            assert authz.user_is_allowed_for_review(user, review.id) is True
            assert (
                authz.user_is_allowed_for_review(user, review.id, for_roles=["owner"])
                is False
            )
        with helpers.set_current_user(outsider.id, db_session) as user:
            assert authz.user_is_allowed_for_review(user, review.id) is False


def test_user_is_allowed_for_user(app, db_session):
    admin = factories.create_user(db_session, is_admin=True)
    user = factories.create_user(db_session)
    collaborator = factories.create_user(db_session)
    outsider = factories.create_user(db_session)
    review = factories.create_review_with_team(
        db_session, owner=user, members=[collaborator]
    )

    with app.app_context():
        with helpers.set_current_user(admin.id, db_session) as current:
            assert authz.user_is_allowed_for_user(current, user.id) is True  # admin
        with helpers.set_current_user(user.id, db_session) as current:
            assert authz.user_is_allowed_for_user(current, user.id) is True  # self
            assert authz.user_is_allowed_for_user(current, collaborator.id) is True
            assert (
                authz.user_is_allowed_for_user(
                    current, collaborator.id, if_collaborator=False
                )
                is False
            )
            assert authz.user_is_allowed_for_user(current, outsider.id) is False
