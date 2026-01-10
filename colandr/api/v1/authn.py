import functools
import typing as t

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app

from ... import models
from ...extensions import db, jwt
from . import errors


# TODO: we should use redis for this
# import celery
# import redis.client
# _JWT_BLOCKLIST = celery.current_app.backend.client
_JWT_BLOCKLIST = set()


@jwt.user_identity_loader
def user_identity_loader(user: models.User | str) -> str:
    """
    Callback function that takes the ``User`` passed in as the "identity"
    when creating JWTs and returns it as a string, either as a stringified ``User.id``
    or as the email associated with the user.
    """
    if isinstance(user, models.User):
        user_identity = str(user.id)
    elif isinstance(user, str):
        user_identity = af.validators.Email()(user)  # validate as email
    else:
        raise ValueError(f"user={user} is invalid")
    return user_identity


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data: dict) -> t.Optional[models.User]:
    """
    Callback function that loads a user from the database by its identity (id)
    whenever a protected API route is accessed.
    """
    user_identity = jwt_data[current_app.config["JWT_IDENTITY_CLAIM"]]
    if user_identity.isdigit():
        user = db.session.get(models.User, int(user_identity))
    elif isinstance(user_identity, str):
        af.validators.Email()(user_identity)  # validate as email
        user = db.session.execute(
            sa.select(models.User).filter_by(email=user_identity)
        ).scalar_one_or_none()
    else:
        raise ValueError(f"user identity={user_identity} is invalid")
    return user


@jwt.additional_claims_loader
def additional_claims_loader(user: models.User | str) -> dict[str, object]:
    """Callback function that adds additional claims to the JWT token."""
    if isinstance(user, models.User):
        return {"is_admin": user.is_admin}
    else:
        return {}


@jwt.token_in_blocklist_loader
def token_in_blocklist_loader(jwt_header, jwt_data: dict) -> bool:
    """
    Callback function that checks if a JWT is in the blocklist, i.e. has been revoked.
    """
    token = jwt_data["jti"]
    # TODO: we should use redis for this
    # token_in_blocklist = _JWT_BLOCKLIST.get(token)
    token_in_blocklist = token in _JWT_BLOCKLIST
    return token_in_blocklist


def authenticate_user(email: str, password: str) -> models.User:
    """
    Verify that password matches the stored password for specified user email;
    if credentials are valid, the corresponding user instance is returned.
    """
    user = db.session.execute(
        sa.select(models.User).filter_by(email=email)
    ).scalar_one_or_none()
    if user is None or user.check_password(password) is False:
        raise ValueError("invalid user email or password")
    return user


def get_user_from_token(token: str) -> t.Optional[models.User]:
    """
    Get a ``User`` from the identity stored in an encoded, unexpired JWT token,
    if it exists in the database; otherwise, return None.
    """
    jwt_data = jwtext.decode_token(token, allow_expired=False)
    identity = jwt_data[current_app.config["JWT_IDENTITY_CLAIM"]]
    if identity.isdigit():
        user = db.session.get(models.User, int(identity))
    elif isinstance(identity, str):
        af.validators.Email()(identity)  # validate as email
        user = db.session.execute(
            sa.select(models.User).filter_by(email=identity)
        ).scalar_one_or_none()
    else:
        raise TypeError(f"user identity={identity} is invalid")
    return user


def pack_header_for_user(user) -> dict[str, str]:
    """
    Create an access token for ``user`` and pack it into a suitable header dict.
    """
    token = jwtext.create_access_token(identity=user, fresh=True)
    header_key = f"{current_app.config['JWT_HEADER_TYPE']} {token}"
    return {current_app.config["JWT_HEADER_NAME"]: header_key}


def jwt_admin_required():
    def wrapper(fn):
        @functools.wraps(fn)
        def decorator(*args, **kwargs):
            jwtext.verify_jwt_in_request()
            jwt_data = jwtext.get_jwt()
            if jwt_data["is_admin"]:
                return fn(*args, **kwargs)
            else:
                raise errors.ForbiddenError(
                    message="this endpoint is for admin users only"
                )

        return decorator

    return wrapper
