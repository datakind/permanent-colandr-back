import functools
import logging
import time
import typing as t

import apiflask as af
import celery
import flask_jwt_extended as jwtext
import redis.client
import redis.exceptions
import sqlalchemy as sa
from flask import current_app

from ... import models
from ...extensions import db, jwt
from . import errors


LOGGER = logging.getLogger(__name__)

JWT_BLOCKLIST_KEY_PREFIX = "jwt_blocklist:"


def _get_redis_client() -> redis.client.Redis:
    """Return the shared Redis client from Celery's result backend."""
    redis_conn = celery.current_app.backend.client
    if not isinstance(redis_conn, redis.client.Redis):
        raise RuntimeError(
            f"Expected Redis backend client, got {type(redis_conn).__name__}"
        )
    return redis_conn


def _blocklist_key(jti: str) -> str:
    return f"{JWT_BLOCKLIST_KEY_PREFIX}{jti}"


def _add_to_blocklist(jti: str, ttl_seconds: int) -> None:
    """Add a JWT ``jti`` to the blocklist with the given TTL."""
    try:
        redis_conn = _get_redis_client()
        redis_conn.set(_blocklist_key(jti), "1", ex=ttl_seconds)
    except Exception as exc:
        LOGGER.error("Cannot add token to blocklist (Redis unavailable): %s", exc)


def _is_blocklisted(jti: str) -> bool:
    """Check whether a JWT ``jti`` is in the blocklist."""
    try:
        redis_conn = _get_redis_client()
        return redis_conn.exists(_blocklist_key(jti)) == 1
    except Exception as exc:
        LOGGER.error(
            "Cannot check token blocklist (Redis unavailable); allowing request: %s",
            exc,
        )
        return False  # fail open


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
    """Callback that checks if a JWT's ``jti`` is in the blocklist, i.e. has been revoked."""
    return _is_blocklisted(jwt_data["jti"])


def revoke_token(jwt_data: dict) -> None:
    """Revoke the JWT for ``jwt_data`` by adding its ``jti`` to the blocklist.

    Blocklist entry expires when the token itself would have expired.
    """
    jti = jwt_data["jti"]
    exp = jwt_data["exp"]
    now = time.time()
    ttl_seconds = max(int(exp - now), 0)
    if ttl_seconds > 0:
        _add_to_blocklist(jti, ttl_seconds)


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
