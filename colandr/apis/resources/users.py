import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Email, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants
from .. import auth
from ..errors import forbidden_error, not_found_error
from ..schemas import UserSchema
from ..swagger import user_model


ns = Namespace("users", path="/users", description="get, create, delete, update users")


@ns.route("/<int:id>")
@ns.doc(
    summary="get, delete, and modify data for single users",
    produces=["application/json"],
)
class UserResource(Resource):
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
        {"fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None)},
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, id, fields):
        """get record for a single user by id"""
        current_user = jwtext.get_current_user()
        if not _is_allowed(current_user, id, collaborators=True):
            return forbidden_error(f"{current_user} forbidden to get this user")

        user = db.session.get(models.User, id)
        if not user:
            return not_found_error(f"<User(id={id})> not found")
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", user)
        return UserSchema(only=fields).dump(user)

    @ns.doc(
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
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        """delete record for a single user by id"""
        current_user = jwtext.get_current_user()
        if not _is_allowed(current_user, id):
            return forbidden_error(f"{current_user} forbidden to delete this user")
        user = db.session.get(models.User, id)
        if not user:
            return not_found_error(f"<User(id={id})> not found")
        db.session.delete(user)
        db.session.commit()
        current_app.logger.info("%s deleted %s", current_user, user)
        return "", 204

    @ns.doc(
        expect=(user_model, "user data to be modified"),
        responses={
            200: "user data was modified",
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
    @jwtext.jwt_required(fresh=True)
    def put(self, args, id):
        """modify record for a single user by id"""
        current_user = jwtext.get_current_user()
        if not _is_allowed(current_user, id):
            return forbidden_error(f"{current_user} forbidden to update this user")
        user = db.session.get(models.User, id)
        if not user:
            return not_found_error(f"<User(id={id})> not found")
        for key, value in args.items():
            if key is missing:
                continue
            else:
                if key == "email":
                    current_app.logger.warning(
                        "%s is modifying %s email, from %s to %s",
                        current_user,
                        user,
                        user.email,
                        value,
                    )
                setattr(user, key, value)
        db.session.commit()
        current_app.logger.info(
            "%s modified %s, attributes=%s", current_user, user, sorted(args.keys())
        )
        return UserSchema().dump(user)


@ns.route("")
@ns.doc(
    summary="get existing and create new users",
    produces=["application/json"],
)
class UsersResource(Resource):
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
            "email": ma_fields.Email(load_default=None, validate=Email()),
            "review_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, email, review_id):
        """get user record(s) for one or more matching users"""
        current_user = jwtext.get_current_user()
        if email:
            # TODO: do we need access checks for this path? should *anyone* be allowed?
            user = db.session.execute(
                sa.select(models.User).filter_by(email=email)
            ).scalar_one_or_none()
            if not user:
                return not_found_error(f'no user found with email "{email}"')
            else:
                current_app.logger.debug("got %s", user)
                # TODO: should we not return this as a 1-item list, for consistency?
                return UserSchema().dump(user)
        elif review_id:
            review = db.session.get(models.Review, review_id)
            if not review:
                return not_found_error(f"<Review(id={review_id})> not found")
            if (
                current_user.is_admin is False
                and review.review_user_assoc.filter_by(
                    user_id=current_user.id
                ).one_or_none()
                is None
            ):
                return forbidden_error(
                    f"{current_user} forbidden to see users for this review"
                )
            return UserSchema(many=True).dump(review.users)

    @ns.doc(
        expect=(user_model, "user data to be created"),
        responses={
            200: "user was created",
            403: "current app user forbidden to create user",
        },
    )
    @use_args(UserSchema(), location="json")
    @auth.jwt_admin_required()
    def post(self, args):
        """create new user (ADMIN ONLY)"""
        user = models.User(**args)
        user.is_confirmed = True
        db.session.add(user)
        db.session.commit()
        current_app.logger.info("inserted %s", user)
        return UserSchema().dump(user)


# def _is_allowed(
#     current_user: models.User, user_id: int, *, collaborators: bool = False
# ) -> bool:
#     is_allowed = current_user.is_admin or user_id == current_user.id
#     if collaborators:
#         is_allowed = is_allowed or any(
#             review.review_user_assoc.filter_by(user_id=user_id).one_or_none()
#             for review in current_user.reviews
#         )
#     return is_allowed


def _is_allowed(
    current_user: models.User,
    user_id: int,
    *,
    admins: bool = True,
    collaborators: bool = False,
) -> bool:
    is_allowed = user_id == current_user.id
    if admins:
        is_allowed = is_allowed or current_user.is_admin
    if collaborators:
        is_allowed = is_allowed or any(
            user.id == user_id for user in current_user.collaborators
        )
    return is_allowed
