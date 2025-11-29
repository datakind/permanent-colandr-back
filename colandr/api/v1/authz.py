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
        (
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
