import flask
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app, render_template
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from ... import tasks
from ...extensions import db
from ...lib import constants
from ...models import Review, ReviewUserAssoc, User
from .. import auth
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import UserSchema


ns = Namespace(
    "review_teams", path="/reviews", description="get, modify, and confirm review teams"
)


@ns.route("/<int:id>/team")
@ns.doc(
    summary="get and modify review teams",
    produces=["application/json"],
)
class ReviewTeamResource(Resource):
    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of user fields to return",
            },
        },
        responses={
            200: "successfully got review team member's records",
            403: "current app user forbidden to get review team member's records",
            404: "no review with matching id was found",
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
        """get members of a single review's team"""
        current_user = jwtext.get_current_user()
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        if (
            current_user.is_admin is False
            and review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(f"{current_user} forbidden to get this review")
        if fields and "id" not in fields:
            fields.append("id")
        users = UserSchema(many=True, only=fields).dump(review.users)
        owner_user_ids = {owner.id for owner in review.owners}
        for user in users:
            user["is_owner"] = user["id"] in owner_user_ids
        current_app.logger.debug("got %s team members for %s", len(users), review)
        return users

    @ns.doc(
        params={
            "action": {
                "in": "query",
                "type": "string",
                "required": True,
                "enum": ["add", "invite", "remove", "make_owner"],
                "description": "add, invite, remove, or promote to owner a particular user",
            },
            "user_id": {
                "in": "query",
                "type": "integer",
                "min": 1,
                "max": constants.MAX_INT,
                "description": "unique id of the user on which to act",
            },
            "user_email": {
                "in": "query",
                "type": "string",
                "format": "email",
                "description": "email address of the user to invite",
            },
            "server_name": {
                "in": "query",
                "type": "string",
                "default": None,
                "description": 'name of server used to build confirmation url, e.g. "http://www.colandrapp.com"',
            },
        },
        responses={
            200: "successfully modified review team member's record",
            403: "current app user forbidden to modify review team",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="view_args",
    )
    @use_kwargs(
        {
            "action": ma_fields.Str(
                required=True, validate=OneOf(["add", "invite", "remove", "make_owner"])
            ),
            "user_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "user_email": ma_fields.Email(load_default=None),
            "server_name": ma_fields.Str(load_default=None),
        },
        location="query",
    )
    @jwtext.jwt_required(fresh=True)
    def put(self, id, action, user_id, user_email, server_name):
        """add, invite, remove, or promote a review team member"""
        current_user = jwtext.get_current_user()
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        if current_user.is_admin is False and current_user not in review.owners:
            return forbidden_error(
                f"{current_user} forbidden to modify this review team"
            )
        if user_id is not None:
            user = db.session.get(User, user_id)
        elif user_email is not None:
            user = db.session.execute(
                sa.select(User).filter_by(email=user_email)
            ).scalar_one_or_none()
            if user is not None:
                user_id = user.id
        else:
            return bad_request_error("user_id or user_email is required")
        review_users = review.users
        # an existing user is being added, without an invite email
        if action == "add":
            if user is None:
                return not_found_error("no user found with given id or email")
            elif current_user.is_admin is False:
                return forbidden_error(f"{current_user} is not an admin")
            elif user in review_users:
                return forbidden_error(f"{user} is already on this review")
            else:
                review_users.append(user)
        # user is being *invited*, so send an invitation email
        elif action == "invite":
            if user is None:
                return not_found_error("no user found with given id or email")
            else:
                token = jwtext.create_access_token(identity=user)
                confirm_url = flask.url_for(
                    "review_teams_confirm_review_team_invite_resource",
                    id=id,
                    token=token,
                    _external=True,
                )
                html = render_template(
                    "emails/invite_user_to_review.html",
                    url=confirm_url,
                    inviter_email=current_user.email,
                    review_name=review.name,
                )
                if current_app.config["MAIL_SERVER"]:
                    tasks.send_email.apply_async(
                        args=[[user.email], "Let's collaborate!", "", html]
                    )
        elif action == "make_owner":
            if user is None:
                return not_found_error("no user found with given id or email")
            review.review_user_assoc.append(ReviewUserAssoc(review, user, "owner"))
        elif action == "remove":
            if user is None:
                return not_found_error("no user found with given id or email")
            review_owners = review.owners
            if user in review_owners and len(review_owners) == 1:
                return forbidden_error("only review owner can not be removed from team")
            if (
                review.review_user_assoc.filter_by(user_id=user_id).one_or_none()
                is not None
            ):
                review.review_user_assoc.remove(ReviewUserAssoc(review, user))

        db.session.commit()
        current_app.logger.info("for %s, %s %s", review, action, user)
        users = UserSchema(many=True).dump(review.users)
        owner_user_ids = {owner.id for owner in review.owners}
        for user in users:
            user["is_owner"] = user["id"] in owner_user_ids
        return users


@ns.route("/<int:id>/team/confirm")
@ns.doc(
    summary="confirm an emailed invitation to join a review team",
    produces=["application/json"],
)
class ConfirmReviewTeamInviteResource(Resource):
    @ns.doc(
        params={
            "token": {
                "in": "query",
                "type": "string",
                "required": True,
                "description": "unique, expiring token included in emailed confirmation url",
            },
        },
        responses={
            200: "successfully modified review team member's record",
            403: "current app user's confirmation token is invalid or has expired",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="view_args",
    )
    @use_kwargs({"token": ma_fields.String(required=True)}, location="query")
    def get(self, id, token):
        """confirm review team invitation via emailed token"""
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        review_users = review.users

        user = auth.get_user_from_token(token)
        if user is None:
            return not_found_error(f"no user found for token='{token}'")

        if user not in review_users:
            review_users.append(user)
        else:
            return forbidden_error(f"{user} is already on this review")

        db.session.commit()
        current_app.logger.info("invitation to %s confirmed by %s", review, user.email)
        users = UserSchema(many=True).dump(review.users)
        owner_user_ids = {owner.id for owner in review.owners}
        for user in users:
            user["is_owner"] = user["id"] in owner_user_ids
        return users
