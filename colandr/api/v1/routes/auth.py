import datetime
import urllib.parse

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
import sqlalchemy.exc
from flask import current_app, render_template, url_for
from flask.views import MethodView

from .... import models, tasks
from ....extensions import db
from .. import authn, errors, schemas


bp = af.APIBlueprint("auth", __name__, url_prefix="/auth")

# TODO: can we bolt our system onto apiflask's built-in httptokenauth?
# auth = af.HTTPTokenAuth(scheme="Bearer")


class LoginAPI(MethodView):
    @bp.doc(
        summary="log-in an existing user",
        description=(
            "Log an existing user in by parsing a POST request containing "
            "user credentials, and issuing valid access and refresh JWT tokens."
        ),
        responses={
            200: "successful login",
            401: "unsuccessful login",
            404: "no user found matching inputs",
        },
    )
    @bp.input(
        {
            "email": af.fields.String(required=True, validate=af.validators.Email()),
            "password": af.fields.String(required=True),
        },
        location="json",
        schema_name="Login",
    )
    @bp.output(
        schemas.TokensSchema,
        example={
            "access_token": "eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoidXNlciIsIklzc3VlciI6Iklzc3VlciIsIlVzZXJuYW1lIjoibmFtZTFAZXhhbXBsZS5jb20iLCJleHAiOjE3NjIxMDcwMTgsImlhdCI6MTc2MjEwNzAxOH0.YqImPu9KGT5PMCTtDvHiCXx_Q1Us5csBZxURHhrDnu4",
            "refresh_token": "eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoidXNlciIsIklzc3VlciI6Iklzc3VlciIsIlVzZXJuYW1lIjoibmFtZTFAZXhhbXBsZS5jb20iLCJleHAiOjE3NjIyNzk4MTgsImlhdCI6MTc2MjEwNzAxOH0.Dy0Q1BdqIxyJVObmdH7NKwyQ5Tuz4v2w0nUMCYkLlYg",
        },
    )
    def post(self, json_data):
        email = json_data["email"]
        password = json_data["password"]
        try:
            user = authn.authenticate_user(email, password)
        except ValueError:
            raise errors.NotFoundError(
                message="no user found matching given email and password"
            )
        if not user.is_confirmed:
            current_app.logger.warning("login by %s, who is not yet confirmed", user)
            # raise errors.UnauthorizedError(
            #     message="user has been created but is not yet confirmed"
            # )
        access_token = jwtext.create_access_token(identity=user, fresh=True)
        refresh_token = jwtext.create_refresh_token(identity=user)
        current_app.logger.info("%s logged in", user)
        return {"access_token": access_token, "refresh_token": refresh_token}


class LogoutAPI(MethodView):
    @bp.doc(
        summary="log-out a user",
        description="Log a user out by revoking the given JWT access token",
        responses={
            200: "successful logout",
            401: "unsuccessful logout",
        },
        security="TokenAuth",
    )
    @bp.output({"message": af.fields.String()})
    @jwtext.jwt_required(verify_type=False)
    def delete(self):
        current_user = jwtext.get_current_user()
        jwt_data = jwtext.get_jwt()
        token = jwt_data["jti"]
        # TODO: we should use redis for this
        # authn._JWT_BLOCKLIST.set(token, "", ex=current_app.config["JWT_REFRESH_TOKEN_EXPIRES"])
        authn._JWT_BLOCKLIST.add(token)
        current_app.logger.info("%s logged out", current_user)
        # TODO: do we *need* to return this message, or nah?
        return {"message": f"{current_user} logged out"}


# TODO: this should be a POST request, right?
class RefreshTokenAPI(MethodView):
    @bp.doc(
        summary="refresh a JWT access token",
        description=(
            "Refresh an existing JWT access token by creating a new copy of the old one "
            "with a refreshed access expiration time"
        ),
        responses={200: "successful token refresh"},
        security="TokenAuth",
    )
    @bp.output(
        schemas.TokenSchema,
        example={
            "access_token": "eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoidXNlciIsIklzc3VlciI6Iklzc3VlciIsIlVzZXJuYW1lIjoibmFtZTFAZXhhbXBsZS5jb20iLCJleHAiOjE3NjIxMDcwMTgsImlhdCI6MTc2MjEwNzAxOH0.YqImPu9KGT5PMCTtDvHiCXx_Q1Us5csBZxURHhrDnu4",
        },
    )
    @jwtext.jwt_required(refresh=True)
    def get(self):
        current_user = jwtext.get_current_user()
        # if we're refreshing, we've probably not verified the user's password in a while
        # so mark the new access token as "not fresh"
        access_token = jwtext.create_access_token(identity=current_user, fresh=False)
        current_app.logger.debug("%s refreshed JWT access token", current_user)
        return {"access_token": access_token}


class RegisterAPI(MethodView):
    @bp.doc(
        summary="register a new user",
        responses={
            200: "successful user registration",
            401: "unsuccessful user registration",
            403: "user with specified params already exists",
        },
    )
    @bp.input(schemas.UserSchema(only=["name", "email", "password"]), location="json")
    @bp.output(schemas.UserSchema)
    def post(self, json_data):
        user = models.User(**json_data)
        try:
            db.session.add(user)
            db.session.commit()
            current_app.logger.info("%s successfully registered", user)
        except sqlalchemy.exc.IntegrityError as e:
            db.session.rollback()
            current_app.logger.error("%s", e.orig)
            raise errors.ForbiddenError(
                message="unable to register user with specified params"
            )

        access_token = jwtext.create_access_token(identity=user, fresh=True)
        _send_confirm_registration_email(user, access_token)
        return user


class RegisterResendAPI(MethodView):
    @bp.doc(
        summary="re-send a registration confirmation email to an uncomfirmed user",
        responses={200: "successfully re-sent confirmation email"},
        security="TokenAuth",
    )
    @bp.output({})
    @jwtext.jwt_required()
    def post(self):
        current_user = jwtext.get_current_user()
        access_token = jwtext.create_access_token(identity=current_user, fresh=True)
        _send_confirm_registration_email(current_user, access_token)


class ConfirmRegistrationAPI(MethodView):
    @bp.doc(
        summary="confirm a new user registration",
        description=(
            "Confirm a user registration using the token they were issued "
            "in their registration email"
        ),
        responses={
            200: "registration successfully confirmed",
            404: "user not found for given token",
        },
    )
    @bp.input({"token": af.fields.String(required=True)}, location="query")
    @bp.output(
        schemas.TokenSchema,
        example={
            "access_token": "eyJhbGciOiJIUzI1NiJ9.eyJSb2xlIjoidXNlciIsIklzc3VlciI6Iklzc3VlciIsIlVzZXJuYW1lIjoibmFtZTFAZXhhbXBsZS5jb20iLCJleHAiOjE3NjIxMDcwMTgsImlhdCI6MTc2MjEwNzAxOH0.YqImPu9KGT5PMCTtDvHiCXx_Q1Us5csBZxURHhrDnu4",
        },
    )
    def get(self, query_data):
        token: str = query_data["token"]
        user = authn.get_user_from_token(token)
        if user is None:
            raise errors.NotFoundError(message=f"no user found for token='{token}'")

        user.is_confirmed = True
        db.session.commit()
        access_token = jwtext.create_access_token(identity=user)
        current_app.logger.info("%s confirmed registration", user)
        return {"access_token": access_token}


class ResetPasswordAPI(MethodView):
    @bp.doc(
        summary="reset a user's password",
        description="reset a user's password by sending an email",
        responses={200: "reset password email sent"},
    )
    @bp.input(
        {"email": af.fields.String(required=True, validate=af.validators.Email())},
        location="query",
    )
    @bp.output({})
    def post(self, query_data):
        email = query_data["email"]
        user = db.session.execute(
            sa.select(models.User).filter_by(email=email)
        ).scalar_one_or_none()
        if user is None:
            current_app.logger.warning(
                "password reset submitted with email='%s', but no such user exists",
                email,
            )
            return

        token_expiration_minutes = 15
        access_token = jwtext.create_access_token(
            identity=user,
            fresh=False,
            expires_delta=datetime.timedelta(minutes=token_expiration_minutes),
        )
        confirm_url = url_for("auth.reset_confirm", token=access_token, _external=True)
        if fe_app_site := current_app.config["FE_APP_SITE"]:
            confirm_url = _replace_url_site(confirm_url, fe_app_site)

        html = render_template(
            "emails/password_reset_v2.html",
            url=confirm_url,
            name=user.name,
            expiration_minutes=token_expiration_minutes,
        )
        if current_app.config["MAIL_SERVER"]:
            tasks.send_email.apply_async(
                args=[[user.email], "Reset your password", "", html]
            )
            current_app.logger.info("password reset email sent to %s", user.email)
        current_app.logger.info("password reset submitted by %s", user)


class ConfirmPasswordResetAPI(MethodView):
    @bp.doc(
        summary="confirm a user's password reset",
        description="confirm a user's password reset via emailed token",
        responses={
            200: "password successfully reset",
            403: "unconfirmed users may not reset passwords",
            404: "no user found for specified token",
            # 422: "invalid or expired password reset link",
        },
    )
    @bp.input({"token": af.fields.String(required=True)}, location="query")
    @bp.input(schemas.UserSchema(only=["password"]), location="json")
    @bp.output(schemas.UserSchema)
    def put(self, query_data, json_data):
        token = query_data["token"]
        password = json_data["password"]
        user = authn.get_user_from_token(token)
        if user is None:
            raise errors.NotFoundError(message=f"no user found for token='{token}'")

        if user.is_confirmed is False:
            raise errors.ForbiddenError(
                message="user not confirmed! please first confirm your email address."
            )

        current_app.logger.info("password reset confirmed for %s", user)
        user.password = password
        db.session.commit()
        return user


bp.add_url_rule("/login", view_func=LoginAPI.as_view("login"))
bp.add_url_rule("/logout", view_func=LogoutAPI.as_view("logout"))
bp.add_url_rule("/refresh", view_func=RefreshTokenAPI.as_view("refresh"))
bp.add_url_rule("/register", view_func=RegisterAPI.as_view("register"))
bp.add_url_rule(
    "/register/resend", view_func=RegisterResendAPI.as_view("register_resend")
)
bp.add_url_rule(
    "/register/confirm", view_func=ConfirmRegistrationAPI.as_view("register_confirm")
)
bp.add_url_rule("/reset", view_func=ResetPasswordAPI.as_view("reset"))
bp.add_url_rule(
    "/reset/confirm", view_func=ConfirmPasswordResetAPI.as_view("reset_confirm")
)


def _replace_url_site(url: str, new_site: str) -> str:
    url_parsed = urllib.parse.urlparse(url)
    # strip out existing scheme and netloc, so we can replace them with new_site
    url_parsed = urllib.parse.urlunparse(url_parsed._replace(scheme="", netloc=""))
    return urllib.parse.urljoin(new_site, url_parsed)


def _send_confirm_registration_email(user: object, access_token: str) -> None:
    assert isinstance(user, models.User)  # type guard
    confirm_url = url_for("auth.register_confirm", token=access_token, _external=True)
    if fe_app_site := current_app.config["FE_APP_SITE"]:
        confirm_url = _replace_url_site(confirm_url, fe_app_site)

    html = render_template(
        "emails/user_registration_v2.html", url=confirm_url, name=user.name
    )
    if current_app.config["MAIL_SERVER"]:
        tasks.send_email.apply_async(
            args=[[user.email], "Confirm your registration", "", html]
        )
        current_app.logger.info("registration email sent to %s", user.email)
