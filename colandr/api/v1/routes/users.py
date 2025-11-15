import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from .. import authz, errors, schemas


bp = af.APIBlueprint("users", __name__, url_prefix="/users")


class UserAPI(MethodView):
    @bp.doc(
        summary="get a single user",
        responses={
            200: "successfully got user record",
            403: "current app user forbidden to get user record",
            404: "no user record matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.UserSchema)
    @jwtext.jwt_required()
    def get(self, id, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()

        if not authz.user_is_allowed_for_user(current_user, id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get this user"
            )

        user = db.session.get(models.User, id)
        if not user:
            raise errors.NotFoundError(message=f"<User(id={id})> not found")

        return models.model_to_dict(user, fields)

    @bp.doc(
        summary="delete a single user",
        responses={
            204: "successfully deleted user record",
            403: "current app user forbidden to delete user record",
            404: "no user record matching id was found",
        },
        security="TokenAuth",
    )
    @bp.output({}, status_code=204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        current_user = jwtext.get_current_user()

        if not authz.user_is_allowed_for_user(current_user, id, if_collaborator=False):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete this user"
            )

        user = db.session.get(models.User, id)
        if not user:
            raise errors.NotFoundError(message=f"<User(id={id})> not found")

        db.session.delete(user)
        db.session.commit()
        current_app.logger.info("%s deleted %s", current_user, user)
        return ""

    @bp.doc(
        summary="modify a single user",
        responses={
            200: "user data was modified",
            403: "current app user forbidden to modify user",
            404: "no user record matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.UserSchema(partial=True), location="json")
    @bp.output(schemas.UserSchema)
    @jwtext.jwt_required(fresh=True)
    def put(self, id, json_data):
        current_user = jwtext.get_current_user()

        if not authz.user_is_allowed_for_user(current_user, id, if_collaborator=False):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to update this user"
            )

        # only admins can add/remove other admins
        if any(key == "is_admin" for key in json_data) and not current_user.is_admin:
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden from assigning admin status"
            )

        user = db.session.get(models.User, id)
        if not user:
            raise errors.NotFoundError(message=f"<User(id={id})> not found")

        for key, value in json_data.items():
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
            "%s modified %s, attributes=%s",
            current_user,
            user,
            sorted(json_data.keys()),
        )
        return user


class UsersAPI(MethodView):
    @bp.doc(
        summary="get user record(s) matching filter",
        responses={
            200: "successfully got user record(s)",
            403: "current app user forbidden to get user record(s)",
            404: "no matching user record(s) found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "email": af.fields.Email(
                validate=af.validators.Email(),
                metadata={"description": "email address of user to get"},
            ),
            "review_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique id of review on which users are collaborators"
                },
            ),
            "admins": af.fields.Boolean(
                validate=af.validators.OneOf([True]),
                metadata={"description": "if True, get all admin users in the system"},
            ),
        },
        location="query",
    )
    @bp.output(schemas.UserSchema(many=True))
    @jwtext.jwt_required()
    def get(self, query_data):
        email = query_data.get("email")
        review_id = query_data.get("review_id")
        admins = query_data.get("admins")
        current_user = jwtext.get_current_user()
        if email is not None:
            user = db.session.execute(
                sa.select(models.User).filter_by(email=email)
            ).scalar_one_or_none()
            if user and not authz.user_is_allowed_for_user(current_user, user.id):
                raise errors.ForbiddenError(
                    message=f"{current_user} forbidden to get this user"
                )
            elif not user:
                raise errors.NotFoundError(
                    message=f'no user found with email "{email}"'
                )
            else:
                current_app.logger.debug("got %s", user)
                return [user]

        elif review_id is not None:
            review = db.session.get(models.Review, review_id)
            if not review:
                raise errors.NotFoundError(
                    message=f"<Review(id={review_id})> not found"
                )
            if (
                current_user.is_admin is False
                and review.review_user_assoc.filter_by(
                    user_id=current_user.id
                ).one_or_none()
                is None
            ):
                raise errors.ForbiddenError(
                    message=f"{current_user} forbidden to see users for this review"
                )
            return review.users

        elif admins is not None:
            if not current_user.is_admin:
                raise errors.ForbiddenError(
                    message=f"{current_user} must be an admin to get all admins"
                )
            admins = db.session.execute(
                sa.select(models.User).filter_by(is_admin=True)
            ).scalars()
            return admins


bp.add_url_rule("/<int:id>", view_func=UserAPI.as_view("user"))
bp.add_url_rule("/", view_func=UsersAPI.as_view("users"))
