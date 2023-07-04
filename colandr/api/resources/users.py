import flask_praetorian
from flask import current_app, g
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Email, Range
from sqlalchemy.exc import IntegrityError, InvalidRequestError
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...extensions import guard
from ...lib import constants
from ...models import Review, User, db
from ..errors import db_integrity_error, forbidden_error, not_found_error
from ..schemas import UserSchema
from ..swagger import user_model


ns = Namespace("users", path="/users", description="get, create, delete, update users")


@ns.route("/<int:id>")
@ns.doc(
    summary="get, delete, and modify data for single users",
    produces=["application/json"],
)
class UserResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of user fields to return",
            },
        },
        responses={
            200: "successfully got user record",
            403: "current app user forbidden to get user record",
            404: "no user with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            )
        },
        location="view_args",
    )
    @use_kwargs(
        {"fields": DelimitedList(ma_fields.String, delimiter=",", missing=None)},
        location="query",
    )
    def get(self, id, fields):
        """get record for a single user by id"""
        if (
            g.current_user.is_admin is False
            and id != g.current_user.id
            and any(
                review.users.filter_by(id=id).one_or_none()
                for review in g.current_user.reviews
            )
            is False
        ):
            return forbidden_error(
                "{} forbidden to get this user".format(g.current_user)
            )
        user = db.session.query(User).get(id)
        if not user:
            return not_found_error("<User(id={})> not found".format(id))
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", user)
        return UserSchema(only=fields).dump(user)

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        responses={
            204: "successfully deleted user record",
            403: "current app user forbidden to delete user record",
            404: "no user with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            )
        },
        location="view_args",
    )
    @use_kwargs({"test": ma_fields.Boolean(missing=False)}, location="query")
    def delete(self, id, test):
        """delete record for a single user by id"""
        if id != g.current_user.id:
            return forbidden_error(
                "{} forbidden to delete this user".format(g.current_user)
            )
        user = db.session.query(User).get(id)
        if not user:
            return not_found_error("<User(id={})> not found".format(id))
        db.session.delete(user)
        if test is False:
            db.session.commit()
            current_app.logger.info("deleted %s", user)
            return "", 204
        else:
            db.session.rollback()

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        body=(user_model, "user data to be modified"),
        responses={
            200: "user data was modified (if test = False)",
            403: "current app user forbidden to modify user",
            404: "no user with matching id was found",
        },
    )
    @use_args(UserSchema(partial=True), location="json")
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            )
        },
        location="view_args",
    )
    @use_kwargs({"test": ma_fields.Boolean(missing=False)}, location="query")
    def put(self, args, id, test):
        """modify record for a single user by id"""
        if id != g.current_user.id:
            return forbidden_error(
                "{} forbidden to update this user".format(g.current_user)
            )
        user = db.session.query(User).get(id)
        if not user:
            return not_found_error("<User(id={})> not found".format(id))
        for key, value in args.items():
            if key is missing:
                continue
            elif key == "password":
                setattr(user, key, guard.hash_password(value))
            else:
                setattr(user, key, value)
        if test is False:
            try:
                db.session.commit()
                current_app.logger.info("modified %s", user)
            except (IntegrityError, InvalidRequestError) as e:
                current_app.logger.exception(
                    "%s: unexpected db error", "UserResource.put"
                )
                db.session.rollback()
                return db_integrity_error(str(e.orig))
        else:
            db.session.rollback()
        return UserSchema().dump(user)


@ns.route("")
@ns.doc(
    summary="get existing and create new users",
    produces=["application/json"],
)
class UsersResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "email": {
                "in": "query",
                "type": "string",
                "description": "email address of user",
            },
            "review_id": {
                "in": "query",
                "type": "integer",
                "description": "unique review id on which users are collaborators",
            },
        },
        responses={
            200: "successfully got user record(s)",
            403: "current app user forbidden to get user record(s)",
            404: "no matching user(s) found",
        },
    )
    @use_kwargs(
        {
            "email": ma_fields.Email(missing=None, validate=Email()),
            "review_id": ma_fields.Int(
                missing=None, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="query",
    )
    def get(self, email, review_id):
        """get user record(s) for one or more matching users"""
        if email:
            user = db.session.query(User).filter_by(email=email).one_or_none()
            if not user:
                return not_found_error('no user found with email "{}"'.format(email))
            else:
                current_app.logger.debug("got %s", user)
                return UserSchema().dump(user)
        elif review_id:
            review = db.session.query(Review).get(review_id)
            if not review:
                return not_found_error("<Review(id={})> not found".format(review_id))
            if (
                g.current_user.is_admin is False
                and review.users.filter_by(id=g.current_user.id).one_or_none() is None
            ):
                return forbidden_error(
                    "{} forbidden to see users for this review".format(g.current_user)
                )
            return UserSchema(many=True).dump(review.users)

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        body=(user_model, "user data to be created"),
        responses={
            200: "user was created (or would have been created if test had been False)",
            403: "current app user forbidden to create user",
        },
    )
    @use_args(UserSchema(), location="json")
    @use_kwargs({"test": ma_fields.Boolean(missing=False)}, location="query")
    def post(self, args, test):
        """create new user (ADMIN ONLY)"""
        if g.current_user.is_admin is False:
            return forbidden_error("UsersResource.post is admin-only")
        user = User(**args)
        user.password = guard.hash_password(user.password)
        user.is_confirmed = True
        db.session.add(user)
        if test is False:
            try:
                db.session.commit()
                current_app.logger.info("inserted %s", user)
            except (IntegrityError, InvalidRequestError) as e:
                current_app.logger.exception(
                    "%s: unexpected db error", "UsersResource.post"
                )
                db.session.rollback()
                return db_integrity_error(str(e.orig))
        else:
            db.session.rollback()
        return UserSchema().dump(user)
