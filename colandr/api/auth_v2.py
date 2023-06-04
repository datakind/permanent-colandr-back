from flask import jsonify
from flask_restx import Namespace, Resource, fields
from marshmallow import fields as ma_fields
from marshmallow.validate import Email
from webargs.flaskparser import use_kwargs

from ..extensions import guard


ns = Namespace(
    "auth", description="authentic API users by checking credentials and issuing tokens"
)

@ns.route("/login")
@ns.doc(
    summary="LOGIN",
    produces=["application/json"],
    responses={
        200: "SUCCESSFUL LOGIN",
        401: "UNSUCCESSFUL LOGIN",
    }
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
        $ curl http://localhost:5000/api/login -X POST \
            -d '{"email":"foo@gmail.com","password":"PASSWORD"}'
        """
        user = guard.authenticate(email, password)
        ret = {"access_token": guard.encode_jwt_token(user)}
        return jsonify(ret)


@ns.route("/refresh")
@ns.doc(
    summary="REFRESH",
    produces=["application/json"],
    responses={
        200: "SUCCESSFUL LOGIN",
        401: "UNSUCCESSFUL LOGIN",
    }
)
class RefreshTokenResource(Resource):

    @ns.doc(responses={})
    def get(self):
        """
        Refresh an existing token by creating a new copy of the old one
        with a refreshed access expiration time.

        .. example::
        $ curl http://localhost:5000/refresh -X GET \
            -H "Authorization: Bearer <your_token>"
        """
        old_token = guard.read_token_from_header()
        new_token = guard.refresh_jwt_token(old_token)
        ret = {"access_token": new_token}
        return jsonify(ret)
