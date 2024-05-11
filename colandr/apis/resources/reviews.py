import os
import shutil

import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants
from ..errors import forbidden_error, not_found_error
from ..schemas import ReviewSchema, ReviewV2Schema
from ..swagger import review_model


ns = Namespace(
    "reviews", path="/reviews", description="get, create, delete, update reviews"
)


@ns.route("/<int:id>")
@ns.doc(
    summary="get, delete, and modify data for single reviews",
    produces=["application/json"],
)
class ReviewResource(Resource):
    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of review fields to return",
            },
        },
        responses={
            200: "successfully got review record",
            403: "current app user forbidden to get review record",
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
        {"fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None)},
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, id, fields):
        """get record for a single review by id"""
        current_user = jwtext.get_current_user()
        if not _is_allowed(current_user, id):
            return forbidden_error(f"{current_user} forbidden to get this review")
        review = db.session.get(models.Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")

        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", review)
        # return ReviewSchema(only=fields).dump(review)
        return _convert_review_v2_into_v1(review, fields)

    @ns.doc(
        responses={
            204: "successfully deleted review record",
            403: "current app user forbidden to delete review record",
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
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        """delete record for a single review by id"""
        current_user = jwtext.get_current_user()
        if not _is_allowed(current_user, id, members=False):
            return forbidden_error(f"{current_user} forbidden to get this review")
        review = db.session.get(models.Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")

        db.session.delete(review)
        db.session.commit()
        current_app.logger.info("deleted %s", review)
        # remove directories on disk for review data
        dirnames = [
            os.path.join(current_app.config["FULLTEXT_UPLOADS_DIR"], str(id)),
            os.path.join(current_app.config["RANKING_MODELS_DIR"], str(id)),
        ]
        for dirname in dirnames:
            shutil.rmtree(dirname, ignore_errors=True)
        return "", 204

    @ns.doc(
        expect=(review_model, "review data to be modified"),
        responses={
            200: "review data was modified",
            403: "current app user forbidden to modify review",
            404: "no review with matching id was found",
        },
    )
    @use_args(ReviewSchema(partial=True), location="json")
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="view_args",
    )
    @jwtext.jwt_required()
    def put(self, args, id):
        """modify record for a single review by id"""
        current_user = jwtext.get_current_user()
        if not _is_allowed(current_user, id, members=False):
            return forbidden_error(f"{current_user} forbidden to get this review")
        review = db.session.get(models.Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")

        for key, value in args.items():
            if key is missing:
                continue
            # HACK: allow setting old attributes, but convert them into new equivalents
            elif key == "num_citation_screening_reviewers":
                review.citation_reviewer_num_pcts = [{"num": value, "pct": 100}]
            elif key == "num_fulltext_screening_reviewers":
                review.fulltext_reviewer_num_pcts = [{"num": value, "pct": 100}]
            else:
                setattr(review, key, value)
        db.session.commit()
        current_app.logger.info("modified %s", review)
        # return ReviewSchema().dump(review)
        return _convert_review_v2_into_v1(review)


@ns.route("")
@ns.doc(
    summary="get existing and create new reviews",
    produces=["application/json"],
)
class ReviewsResource(Resource):
    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of review fields to return",
            },
            "_review_ids": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of review ids to return (ADMIN ONLY)",
            },
        },
        responses={
            200: "successfully got review record(s)",
            403: 'a non-admin user passed admin-only "_review_ids" param',
        },
    )
    @use_kwargs(
        {
            "fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None),
            "_review_ids": DelimitedList(
                ma_fields.String, delimiter=",", load_default=None
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, fields, _review_ids):
        """get all reviews on which current app user is a collaborator"""
        current_user = jwtext.get_current_user()
        if current_user.is_admin is True and _review_ids is not None:
            reviews = (
                db.session.execute(
                    sa.select(models.Review).filter(
                        models.Review.id == sa.any_(_review_ids)
                    )
                )
                .scalars()
                .all()
            )
        elif current_user.is_admin is False and _review_ids is not None:
            return forbidden_error(
                f'non-admin {current_user} passed admin-only "_review_ids" param'
            )
        else:
            reviews = current_user.reviews
        if fields and "id" not in fields:
            fields.append("id")
        # return ReviewSchema(only=fields, many=True).dump(reviews)
        return [_convert_review_v2_into_v1(review) for review in reviews]

    @ns.doc(
        expect=(review_model, "review data to be created"),
        responses={200: "review was created"},
    )
    @use_args(ReviewSchema(), location="json")
    @jwtext.jwt_required()
    def post(self, args):
        """create new review"""
        current_user = jwtext.get_current_user()
        name = args.pop("name")
        review = models.Review(name=name, **args)  # type: ignore
        # TODO: do we want to allow admins to set other users as owners?
        review.review_user_assoc.append(
            models.ReviewUserAssoc(review, current_user, "owner")
        )
        db.session.add(review)
        db.session.commit()
        current_app.logger.info("inserted %s", review)
        # create directories on disk for review data
        dirnames = [
            os.path.join(current_app.config["FULLTEXT_UPLOADS_DIR"], str(review.id)),
            os.path.join(current_app.config["RANKING_MODELS_DIR"], str(review.id)),
        ]
        for dirname in dirnames:
            try:
                os.makedirs(dirname, exist_ok=True)
            except OSError:
                pass  # TODO: fix this / the entire system for saving files to disk
        # return ReviewSchema().dump(review)
        return _convert_review_v2_into_v1(review)


def _is_allowed(
    current_user: models.User, review_id: int, *, members: bool = True
) -> bool:
    is_allowed = current_user.is_admin
    if members:
        is_allowed = (
            is_allowed
            or db.session.execute(
                current_user.review_user_assoc.select().filter_by(review_id=review_id)
            ).one_or_none()
            is not None
        )
    else:
        is_allowed = is_allowed or any(
            review.id == review_id for review in current_user.owned_reviews
        )

    return is_allowed


def _convert_review_v2_into_v1(review, fields=None) -> dict:
    record = ReviewV2Schema(only=fields).dump(review)
    assert isinstance(record, dict)
    if record.get("citation_reviewer_num_pcts"):
        record["num_citation_screening_reviewers"] = record.pop(
            "citation_reviewer_num_pcts"
        )[0]["num"]
    if record.get("fulltext_reviewer_num_pcts"):
        record["num_fulltext_screening_reviewers"] = record.pop(
            "fulltext_reviewer_num_pcts"
        )[0]["num"]
    return record
