from flask import jsonify
from flask_restx import Namespace, Resource, fields
from marshmallow import fields as ma_fields
from marshmallow.validate import Email
from webargs.flaskparser import use_args, use_kwargs

from ..extensions import db, guard
from ..models import User
from .schemas import UserSchema
from .swagger import user_model


ns = Namespace(
    "auth",
    path="/auth",
    description=(
        "register and confirm new API users, authentic against given credentials, "
        "and issue/refresh API tokens"
    ),
)

@ns.route(
    "/login",
    doc={
        "summary": "LOGIN",
        "produces": ["application/json"],
        "responses": {
            200: "SUCCESSFUL LOGIN",
            401: "UNSUCCESSFUL LOGIN",
        },
    },
)
class LoginResource(Resource):

    @ns.doc(
        body=(
            ns.model(
                "Login",
                {"email": fields.String(required=True), "password": fields.String(required=True)}
            ),
            "login info",
        ),
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
        "summary": "REFRESH",
        "produces": ["application/json"],
        "responses": {
            200: "SUCCESSFUL REFRESH",
            401: "UNSUCCESSFUL REFRESH",
        },
    },
)
class RefreshTokenResource(Resource):

    @ns.doc(security="access_token")
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
            200: "SUCCESSFUL REGISTER",
            401: "UNSUCCESSFUL REGISTER",
        },
    },
)
class RegisterResource(Resource):

    @ns.doc(
        body=(user_model, "user data to be registered"),
    )
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
        db.session.add(user)
        db.session.commit()
        # TODO: figure this out
        # guard.send_registration_email(user.email, user=user)
        ret = {"message": f"successfully sent registration email to {user.email}"}
        return jsonify(ret)


@ns.route(
    "/confirm",
    doc={
        "summary": "CONFIRM",
        "produces": ["application/json"],
        "responses": {
            200: "SUCCESSFUL CONFIRM",
            401: "UNSUCCESSFUL CONFIRM",
        },
    },
)
class ConfirmRegistrationResource(Resource):

    @ns.doc(security="access_token")
    def get(self):
        """
        Confirm a user registration using the token they were issued in their
        registration email.

        .. example::
        $ curl http://localhost:5000/api/auth/confirm -X GET \
            -H "Authorization: Bearer <your_token>"
        """
        registration_token = guard.read_token_from_header()
        user = guard.get_user_from_registration_token(registration_token)
        user.is_confirmed = True
        db.session.commit()
        ret = {"access_token": guard.encode_jwt_token(user)}
        return jsonify(ret)
