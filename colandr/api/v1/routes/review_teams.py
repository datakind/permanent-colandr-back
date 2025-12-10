import typing as t

import apiflask as af
import flask
import flask_jwt_extended as jwtext
import marshmallow as ma
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models, tasks
from ....extensions import cache, db
from .. import authn, authz, errors, schemas
from . import auth


bp = af.APIBlueprint("review_teams", __name__, url_prefix="/reviews")


class UserSchemaPlusOwner(schemas.UserSchema):
    is_owner = af.fields.Boolean()


class ReviewTeamPutSchema(af.Schema):
    action = af.fields.String(
        required=True,
        validate=af.validators.OneOf(
            ["add", "invite", "remove", "make_owner", "set_role"]
        ),
        metadata={
            "description": "add, invite, remove, or set the role for a particular user"
        },
    )
    user_id = af.fields.Integer(
        validate=af.validators.Range(min=1),
        metadata={"description": "unique id of the user on which to act"},
    )
    user_email = af.fields.String(
        validate=af.validators.Email(),
        metadata={"description": "unique email address of the user on which to act"},
    )
    user_role = af.fields.String(
        validate=af.validators.OneOf(["member", "owner"]),
        metadata={"description": "type of role to set for user on review"},
    )

    @ma.post_load
    def add_id_if_not_specified(self, data: dict, **kwargs) -> dict:
        if data.get("user_id") is None and data.get("user_email") is None:
            raise ma.ValidationError(
                "at least one of 'user_id' and 'user_email' must be specified"
            )
        return data


class ReviewTeamAPI(MethodView):
    @bp.doc(
        summary="get members of a single review's team",
        responses={
            200: "successfully got review team member's records",
            403: "current app user forbidden to get review team member's records",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(UserSchemaPlusOwner(many=True))
    @jwtext.jwt_required()
    def get(self, id, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        if (
            current_user.is_admin is False
            and review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get this review"
            )

        team = _get_review_team(review, fields=fields)

        current_app.logger.debug(
            "%s got %s team members for %s", current_user, len(team), review
        )
        return team

    @bp.doc(
        summary="add, invite, remove, or set the role for a single user",
        responses={
            200: "successfully modified review team member's record",
            403: "current app user forbidden to modify review team",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(ReviewTeamPutSchema, location="query")
    @bp.output(UserSchemaPlusOwner(many=True))
    @jwtext.jwt_required(fresh=True)
    def put(self, id, query_data):
        action = query_data["action"]
        user_id = query_data.get("user_id")
        user_email = query_data.get("user_email")
        user_role = query_data.get("user_role")
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        if (
            current_user.is_admin is False and current_user not in review.owners
        ) or review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to modify this review team"
            )

        if user_id is not None:
            user = db.session.get(models.User, user_id)
        elif user_email is not None:
            user = db.session.execute(
                sa.select(models.User).filter_by(email=user_email)
            ).scalar_one_or_none()
            if user is not None:
                user_id = user.id
        else:
            # NOTE: this shouldn't be possible, given the input schema validation
            raise errors.BadRequestError(message="user_id or user_email is required")

        review_users = review.users
        # an existing user is being added, without an invite email
        if action == "add":
            if user is None:
                raise errors.NotFoundError(
                    message="no user found with given id or email"
                )
            elif current_user.is_admin is False:
                raise errors.ForbiddenError(message=f"{current_user} is not an admin")
            elif user in review_users:
                raise errors.ForbiddenError(message=f"{user} is already on this review")
            else:
                review.review_user_assoc.append(models.ReviewUserAssoc(review, user))
        # user is being *invited*, so send an invitation email
        elif action == "invite":
            if user is not None:
                identity = user
                user_email = user.email
                template_name = "emails/invite_user_to_review.html"
            else:
                identity = user_email
                template_name = "emails/invite_new_user_to_review.html"
            token = jwtext.create_access_token(identity=identity)
            confirm_url = flask.url_for(
                "review_teams.review_team_confirmation",
                id=id,
                token=token,
                _external=True,
            )
            if fe_app_site := current_app.config["FE_APP_SITE"]:
                confirm_url = auth._replace_url_site(confirm_url, fe_app_site)
            html = flask.render_template(
                template_name,
                url=confirm_url,
                inviter_email=current_user.email,
                review_name=review.name,
            )
            if current_app.config["MAIL_SERVER"]:
                tasks.send_email.apply_async(
                    args=[[user_email], "Let's collaborate!", "", html]
                )
        elif action in ("make_owner", "set_role"):
            if user is None:
                raise errors.NotFoundError(
                    message="no user found with given id or email"
                )
            rua = review.review_user_assoc.filter_by(user_id=user_id).one_or_none()
            if rua is None:
                raise errors.NotFoundError(
                    message="no user found with access to this review"
                )
            else:
                rua.user_role = "owner" if action == "make_owner" else user_role
        elif action == "remove":
            if user is None:
                raise errors.NotFoundError(
                    message="no user found with given id or email"
                )
            review_owners = review.owners
            if user in review_owners and len(review_owners) == 1:
                raise errors.ForbiddenError(
                    message="only review owner can not be removed from team"
                )
            rua = review.review_user_assoc.filter_by(user_id=user_id).one_or_none()
            if rua is not None:
                db.session.delete(rua)

        db.session.commit()
        authz.clear_cache(current_user, review_id=review.id)
        current_app.logger.info(
            "for %s, %s invoked the '%s' action on %s",
            review,
            current_user,
            action,
            user,
        )
        team = _get_review_team(review, fields=None)
        return team


class ReviewTeamConfirmationAPI(MethodView):
    @bp.doc(
        summary="confirm review team invitation via emailed token",
        responses={
            200: "successfully modified review team member's record",
            403: "current app user's confirmation token is invalid or has expired",
            404: "no review with matching id was found",
        },
    )
    @bp.input(
        {
            "token": af.fields.String(
                required=True,
                metadata={
                    "description": "unique, expiring token included in emailed confirmation url"
                },
            )
        },
        location="query",
    )
    @bp.output(UserSchemaPlusOwner(many=True))
    def get(self, id, query_data):
        token: str = query_data["token"]
        user = authn.get_user_from_token(token)
        review = db.session.get(models.Review, id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        if user is None:
            raise errors.NotFoundError(message=f"no user found for token='{token}'")

        if user in review.users:
            raise errors.ForbiddenError(message=f"{user} is already on this review")

        db.session.add(models.ReviewUserAssoc(review, user))
        db.session.commit()
        authz.clear_cache(user, review_id=review.id)

        current_app.logger.info("invitation to %s confirmed by %s", review, user.email)
        team = _get_review_team(review, fields=None)
        return team


bp.add_url_rule("/<int:id>/team", view_func=ReviewTeamAPI.as_view("review_team"))
bp.add_url_rule(
    "/<int:id>/team/confirm",
    view_func=ReviewTeamConfirmationAPI.as_view("review_team_confirmation"),
)


def _get_review_team(
    review: models.Review, fields: t.Optional[list[str]] = None
) -> list[dict]:
    owner_user_ids = {owner.id for owner in review.owners}
    users = [models.model_to_dict(user, fields) for user in review.users]
    # TODO: don't always include is-owner, maybe?
    # if fields is None or "is_owner" in fields:
    for user in users:
        user["is_owner"] = user["id"] in owner_user_ids
    return users
