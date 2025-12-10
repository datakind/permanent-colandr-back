import typing as t
from collections.abc import Collection

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from ... import models
from ...extensions import cache, db


@cache.memoize()
def user_is_allowed_for_review(
    user: models.User,
    review_id: int,
    *,
    for_roles: Collection[str] = ("owner", "member"),
    if_frozen: bool = True,
) -> bool:
    """
    Args:
        user: current app user trying to access review
        review_id: unique identifier for review to be accessed
        for_roles: user roles for which access is authorized
        if_frozen: if True, no access allowed for reviews with "frozen" status;
            otherwise, access is allowed for eligible users

    Returns:
        True if user is allowed to access review; False otherwise
    """
    review = db.session.get(models.Review, review_id)
    review_user_assoc = (
        sa.select(models.ReviewUserAssoc)
        .where(models.ReviewUserAssoc.user_id == user.id)
        .where(models.ReviewUserAssoc.review_id == review_id)
        .where(models.ReviewUserAssoc.user_role == sa.any_(pg.array(for_roles)))
    )
    return (
        # only confirmed users are allowed
        user.is_confirmed
        and (
            # admin users are allowed
            user.is_admin is True
            # users associated with review having specified role(s) are allowed
            or db.session.execute(review_user_assoc).scalar_one_or_none() is not None
        )
        # allowed is conditional on review being frozen or not
        and (if_frozen is True or review.status != "frozen")  # type: ignore
    )


@cache.memoize()
def user_is_allowed_for_user(
    user: models.User, user_id: int, *, if_collaborator: bool = True
) -> bool:
    """
    Args:
        user: current app user trying to access user
        user_id: unique identifier for user to be accessed
        if_collaborator: if True, access is allowed for users who are collaborators

    Returns:
        True if user is allowed to access user; False otherwise
    """
    return (
        # only confirmed users are allowed
        user.is_confirmed
        and (
            # current user same as user is allowed
            user.id == user_id
            # admin users are allowed
            or user.is_admin is True
            # users who are collaborators with specified user may be allowed
            or (
                if_collaborator is True
                and any(collab.id == user_id for collab in user.collaborators)
            )
        )
    )


def clear_cache(
    user: models.User,
    review_id: t.Optional[int] = None,
    user_id: t.Optional[int] = None,
) -> None:
    """
    Clear cached authz funcs when results are expected to change, e.g. a user's role
    is changed or they're added to a review team.

    Args:
        user: app user for which authorization has changed
        review_id: if specified, only clear cache for corresponding user-review authz
        user_id: if specified, only clear cache for corresponding user-user authz
    """
    if review_id is None:
        cache.delete_memoized(user_is_allowed_for_review)
    else:
        for for_roles in [["member"], ["owner"], ("owner", "member")]:
            for if_frozen in [True, False]:
                cache.delete_memoized(
                    user_is_allowed_for_review,
                    user,
                    review_id,
                    for_roles=for_roles,
                    if_frozen=if_frozen,
                )
    if user_id is None:
        cache.delete_memoized(user_is_allowed_for_user)
    else:
        for if_collaborator in [True, False]:
            cache.delete_memoized(
                user_is_allowed_for_user, user, user_id, if_collaborator=if_collaborator
            )
