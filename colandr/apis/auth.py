import functools
from typing import Optional

import flask_jwt_extended as jwtext
from flask import current_app, render_template, url_for
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Email
from webargs.flaskparser import use_args, use_kwargs

from .. import tasks
from ..extensions import db, jwt
from ..models import User
from .errors import db_integrity_error, forbidden_error, not_found_error
from .schemas import UserSchema
from .swagger import login_model, user_model


ns = Namespace(
    "auth",
    path="/auth",
    description=(
        "register and confirm new API users, login and authorize existing users, "
        "issue/refresh API tokens, and handle password reset requests"
    ),
)

JWT_BLOCKLIST = set()  # TODO: we should really use redis for this ...


@ns.route(
    "/login",
    doc={
        "summary": "log-in existing users via email and password, producing API tokens",
        "produces": ["application/json"],
        "responses": {
            200: "successful login",
            401: "unsuccessful login",
        },
    },
)
class LoginResource(Resource):
    @ns.doc(
        expect=(
            login_model,
            "login credentials (email and password) for existing user",
        ),
        responses={},
    )
    @use_kwargs(
        {
            "email": ma_fields.String(required=True, validate=Email()),
            "password": ma_fields.String(required=True),
        },
        location="json",
    )
    def post(self, email, password):
        """
        Log a user in by parsing a POST request containing user credentials and
        issuing a JWT token.

        .. example::
        $ curl http://localhost:5000/api/auth/login -X POST \
            -d '{"email":"foo@gmail.com","password":"PASSWORD"}'
        """
        user = authenticate_user(email, password)
        access_token = jwtext.create_access_token(identity=user, fresh=True)
        refresh_token = jwtext.create_refresh_token(identity=user)
        return {"access_token": access_token, "refresh_token": refresh_token}


# TODO: logout, including jwt revokation


@ns.route(
    "/refresh",
    doc={
        "summary": "refresh an existing API token upon its expiration",
        "produces": ["application/json"],
        "responses": {
            200: "successful token refresh",
            401: "unsuccessful token refresh",
        },
    },
)
class RefreshTokenResource(Resource):
    @ns.doc()
    @jwtext.jwt_required(refresh=True)
    def get(self):
        """
        Refresh an existing token by creating a new copy of the old one
        with a refreshed access expiration time.

        .. example::
        $ curl http://localhost:5000/api/auth/refresh -X GET \
            -H "Authorization: Bearer <your_token>"
        """
        user = jwtext.get_current_user()
        access_token = jwtext.create_access_token(identity=user, fresh=False)
        return {"access_token": access_token}


@ns.route(
    "/register",
    doc={
        "summary": "REGISTER",
        "produces": ["application/json"],
        "responses": {
            200: "successful user registration",
            401: "unsuccessful user registration",
        },
    },
)
class RegisterResource(Resource):
    @ns.doc(expect=(user_model, "new user data to be registered"))
    @use_args(UserSchema(), location="json")
    def post(self, args):
        """
        Register a new user.

        .. example::
        $ curl http://localhost:5000/auth/register -X POST \
            -d '{
                "name": "NAME", \
                "email":"EMAIL", \
                "password":"PASSWORD" \
            }'
        """
        if User.lookup(args["email"]) is not None:
            return db_integrity_error(
                f"email={args['email']} already assigned to user in database"
            )

        user = User(**args)
        db.session.add(user)
        db.session.commit()
        current_app.logger.info("%s successfully registered", user)

        access_token = jwtext.create_access_token(identity=user, fresh=True)
        confirm_url = url_for("auth_confirm_registration_resource", _external=True)
        html = render_template(
            "emails/user_registration.html",
            action_uri=confirm_url,
            token=access_token,
        )
        if current_app.config["MAIL_SERVER"]:
            tasks.send_email.apply_async(
                args=[[user.email], "Confirm your registration", "", html]
            )
            current_app.logger.info(
                "successfully sent registration email to %s", user.email
            )
        return UserSchema().dump(user)


@ns.route(
    "/register/confirm",
    doc={
        "summary": "confirm a new user registration",
        "produces": ["application/json"],
        "responses": {
            200: "successful registration confirmation",
            401: "unsuccessful registration confirmation",
        },
    },
)
class ConfirmRegistrationResource(Resource):
    @ns.doc(params={"token": {"in": "query", "type": "string", "required": True}})
    @use_kwargs({"token": ma_fields.Str(required=True)}, location="query")
    def get(self, token):
        """
        Confirm a user registration using the token they were issued in their
        registration email.

        .. example::
        $ curl http://localhost:5000/api/auth/confirm?token=<TOKEN> -X GET
        """
        user = get_user_from_token(token)
        if user is None:
            return not_found_error(f"no user found for token='{token}'")
        user.is_confirmed = True
        db.session.commit()
        access_token = jwtext.create_access_token(identity=user)
        return {"access_token": access_token}


@ns.route(
    "/reset",
    doc={
        "summary": "reset a user's password by sending an email",
        "produces": ["application/json"],
    },
)
class ResetPasswordResource(Resource):
    @ns.doc(
        params={
            "email": {
                "in": "query",
                "type": "string",
                "required": True,
                "description": "email of user whose password is to be reset",
            },
            # 'server_name': {'in': 'query', 'type': 'string', 'default': None,
            #                 'description': 'name of server used to build confirmation url, e.g. "http://www.colandrapp.com"'},
        },
        responses={
            200: "user was created (or would have been created if test had been False)",
            401: "current app user not authorized to create user",
        },
    )
    @use_kwargs(
        {
            "email": ma_fields.Str(required=True, validate=Email()),
            # "server_name": ma_fields.Str(load_default=None),
        },
        location="query",
    )
    def post(self, email):
        user = User.lookup(email)
        if user is None:
            current_app.logger.warning(
                "password reset submitted with email='%s', but no such user exists",
                email,
            )
        else:
            access_token = jwtext.create_access_token(identity=user, fresh=False)
            confirm_url = url_for(
                "auth_confirm_reset_password_resource", _external=True
            )
            html = render_template(
                "emails/password_reset.html",
                action_uri=confirm_url,
                token=access_token,
            )
            if current_app.config["MAIL_SERVER"]:
                tasks.send_email.apply_async(
                    args=[[user.email], "Reset your password", "", html]
                )


@ns.route(
    "/reset/confirm",
    doc={
        "summary": "confirm a user's password reset via emailed token",
        "produces": ["application/json"],
    },
)
class ConfirmResetPasswordResource(Resource):
    @ns.doc(
        params={
            "token": {"in": "query", "type": "string", "required": True},
            "password": {
                "in": "body",
                "type": "string",
                "required": True,
                "description": "new user password to be set",
            },
        },
        responses={
            200: "password successfully reset",
            404: "no user found with given email",
            422: "invalid or expired password reset link",
        },
    )
    @use_args(UserSchema(only=["password"]), location="json")
    @use_kwargs({"token": ma_fields.Str(required=True)}, location="query")
    def put(self, args, token):
        """confirm a user's password reset via emailed token"""
        user = get_user_from_token(token)
        if user is None:
            return not_found_error(f"no user found for token='{token}'")
        elif user.is_confirmed is False:
            return forbidden_error(
                "user not confirmed! please first confirm your email address."
            )
        current_app.logger.info("password reset confirmed by %s", user.email)
        user.password = args["password"]
        db.session.commit()
        return UserSchema().dump(user)


@jwt.user_identity_loader
def user_identity_loader(user: User):
    """
    Callback function that takes the ``User`` passed in as the "identity"
    when creating JWTs and returns it in JSON serializable format,
    i.e. as the corresponding unique integer ``User.id`` .
    """
    return user.id


@jwt.user_lookup_loader
def user_lookup_callback(_jwt_header, jwt_data: dict) -> User:
    """
    Callback function that loads a user from the database by its identity (id)
    whenever a protected API route is accessed.
    """
    identity = jwt_data[current_app.config["JWT_IDENTITY_CLAIM"]]
    user = db.session.get(User, identity)
    return user


@jwt.additional_claims_loader
def additional_claims_loader(user: User) -> dict:
    return {"is_admin": user.is_admin}


@jwt.token_in_blocklist_loader
def token_in_blocklist_loader(jwt_header, jwt_data: dict) -> bool:
    """
    Callback function that checks if a JWT is in the blocklist, i.e. has been revoked.
    """
    token = jwt_data["jti"]
    token_in_blocklist = token in JWT_BLOCKLIST
    return token_in_blocklist


def jwt_admin_required():
    def wrapper(fn):
        @functools.wraps(fn)
        def decorator(*args, **kwargs):
            jwtext.verify_jwt_in_request()
            jwt_data = jwtext.get_jwt()
            if jwt_data["is_admin"]:
                return fn(*args, **kwargs)
            else:
                return ({"msg": "this endpoint is for admin users only"}, 403)

        return decorator

    return wrapper


def authenticate_user(email: str, password: str) -> User:
    """
    Verify that password matches the stored password for specified user email;
    if credentials are valid, the corresponding user instance is returned.
    """
    user = User.lookup(email)
    if user is None or user.check_password(password) is False:
        raise ValueError("invalid user email or password")
    else:
        current_app.logger.info(
            "%s successfully authenticated using email='%s'", user, email
        )
        return user


def get_user_from_token(token: str) -> Optional[User]:
    """
    Get a ``User`` from the identity stored in an encoded, unexpired JWT token,
    if it exists in the database; otherwise, return None.
    """
    jwt_data = jwtext.decode_token(token, allow_expired=False)
    user_id = jwt_data[current_app.config["JWT_IDENTITY_CLAIM"]]
    user = db.session.get(User, user_id)
    return user


def pack_header_for_user(user) -> dict[str, str]:
    """
    Create an access token for ``user`` and pack it into a suitable header dict.
    """
    token = jwtext.create_access_token(identity=user, fresh=True)
    header_key = f"{current_app.config['JWT_HEADER_TYPE']} {token}"
    return {current_app.config["JWT_HEADER_NAME"]: header_key}
