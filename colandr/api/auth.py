from flask import current_app, jsonify, render_template, url_for
from flask_restx import Namespace, Resource, fields
from marshmallow import fields as ma_fields
from marshmallow.validate import Email
from webargs.flaskparser import use_args, use_kwargs

from ..extensions import db, guard
from ..models import User
from .errors import forbidden_error, not_found_error
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
        body=(login_model, "login credentials (email and password) for existing user"),
        responses={},
    )
    @use_kwargs(
        {
            "email": ma_fields.String(required=True, validate=Email()),
            "password": ma_fields.String(required=True),
        }
    )
    def post(self, email, password):
        """
        Log a user in by parsing a POST request containing user credentials and
        issuing a JWT token.

        .. example::
        $ curl http://localhost:5000/api/auth/login -X POST \
            -d '{"email":"foo@gmail.com","password":"PASSWORD"}'
        """
        user = guard.authenticate(email, password)
        ret = {"access_token": guard.encode_jwt_token(user)}
        return jsonify(ret)


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
    def get(self):
        """
        Refresh an existing token by creating a new copy of the old one
        with a refreshed access expiration time.

        .. example::
        $ curl http://localhost:5000/api/auth/refresh -X GET \
            -H "Authorization: Bearer <your_token>"
        """
        old_token = guard.read_token_from_header()
        new_token = guard.refresh_jwt_token(old_token)
        ret = {"access_token": new_token}
        return jsonify(ret)


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
    @ns.doc(body=(user_model, "new user data to be registered"))
    @use_args(UserSchema())
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
        user = User(**args)
        user.password = guard.hash_password(user.password)
        confirm_url = url_for("auth_confirm_registration_resource", _external=True)
        # TODO: if we use our own template, we must keep url + token separate
        # since flask praetorian passes them in separately under the hood
        # for consistency, we should include token as a param on the url
        # html = render_template(
        #     "emails/user_registration.html",
        #     username=user.name,
        #     confirm_url=confirm_url,
        # )
        db.session.add(user)
        db.session.commit()
        if current_app.config["MAIL_SERVER"]:
            guard.send_registration_email(
                user.email,
                user=user,
                confirmation_uri=confirm_url,
                confirmation_sender=current_app.config["MAIL_DEFAULT_SENDER"],
                subject=f"{current_app.config['MAIL_SUBJECT_PREFIX']} Confirm your registration",
                # template=html,
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
    @use_kwargs({"token": ma_fields.Str(required=True)})
    def get(self, token):
        """
        Confirm a user registration using the token they were issued in their
        registration email.

        .. example::
        $ curl http://localhost:5000/api/auth/confirm?token=<TOKEN> -X GET
        """
        user = guard.get_user_from_registration_token(token)
        user.is_confirmed = True
        db.session.commit()
        ret = {"access_token": guard.encode_jwt_token(user)}
        return jsonify(ret)


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
            # "server_name": ma_fields.Str(missing=None),
        }
    )
    def post(self, email):
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if user is None:
            current_app.logger.warning(
                "password reset submitted with email='%s', but no such user exists",
                email,
            )
        else:
            confirm_url = url_for(
                "auth_confirm_reset_password_resource", _external=True
            )
            # TODO: same as for user registration resource
            # html = render_template(
            #     "emails/password_reset.html", username=user.name, confirm_url=confirm_url
            # )
            if current_app.config["MAIL_SERVER"]:
                guard.send_reset_email(
                    user.email,
                    reset_uri=confirm_url,
                    reset_sender=current_app.config["MAIL_DEFAULT_SENDER"],
                    subject=f"{current_app.config['MAIL_SUBJECT_PREFIX']} Reset your password",
                    # template=html,
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
    @use_args(UserSchema(only=["password"]))
    @use_kwargs({"token": ma_fields.Str(required=True)})
    def put(self, args, token):
        """confirm a user's password reset via emailed token"""
        user = guard.validate_reset_token(token)
        if user is None:
            return not_found_error(f"no user found for token='{token}'")
        elif user.is_confirmed is False:
            return forbidden_error(
                "user not confirmed! please first confirm your email address."
            )
        current_app.logger.info("password reset confirmed by %s", user.email)
        user.password = guard.hash_password(args["password"])
        db.session.commit()
        return UserSchema().dump(user)
