import datetime
import os
import shutil
import typing as t

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from .. import authz, errors, schemas


bp = af.APIBlueprint("reviews", __name__, url_prefix="/reviews")


class ReviewAPI(MethodView):
    @bp.doc(
        summary="get a single review",
        responses={
            200: "successfully got review record",
            403: "current app user forbidden to get review record",
            404: "no review record matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.ReviewSchema)
    @jwtext.jwt_required()
    def get(self, id, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get this review"
            )

        review = db.session.get(models.Review, id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        result = _convert_review_v2_into_v1(review, fields)
        return result

    @bp.doc(
        summary="delete a single review",
        responses={
            204: "successfully deleted review record",
            403: "current app user forbidden to delete review record",
            404: "no review record matching id was found",
        },
        security="TokenAuth",
    )
    @bp.output({}, status_code=204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, id, for_roles=["owner"]):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete this review"
            )

        review = db.session.get(models.Review, id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        db.session.delete(review)
        db.session.commit()
        current_app.logger.info("deleted %s", review)
        # remove directories on disk for review data
        dirnames = [
            os.path.join(current_app.config["FULLTEXT_UPLOADS_DIR"], str(id)),
            os.path.join(current_app.config["CITATION_UPLOADS_DIR"], f"review_{id:08}"),
            os.path.join(current_app.config["RANKER_MODELS_DIR"], f"review_{id:08}"),
        ]
        for dirname in dirnames:
            shutil.rmtree(dirname, ignore_errors=True)
        return ""

    @bp.doc(
        summary="modify a single review",
        responses={
            200: "review data was modified",
            403: "current app user forbidden to modify review",
            404: "no review record matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.ReviewSchema(partial=True), location="json")
    @bp.output(schemas.ReviewSchema)
    @jwtext.jwt_required()
    def put(self, id, json_data):
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, id, for_roles=["owner"]):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get this review"
            )

        review = db.session.get(models.Review, id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        for key, value in json_data.items():
            # HACK: allow setting old attributes, but convert them into new equivalents
            if key == "num_citation_screening_reviewers":
                review.citation_reviewer_num_pcts = [{"num": value, "pct": 100}]
            elif key == "num_fulltext_screening_reviewers":
                review.fulltext_reviewer_num_pcts = [{"num": value, "pct": 100}]
            else:
                setattr(review, key, value)
        db.session.commit()
        current_app.logger.info("modified %s", review)
        return _convert_review_v2_into_v1(review)


class ReviewsAPI(MethodView):
    @bp.doc(
        summary="get review(s)",
        description="get review(s) on which current app user is a collaborator",
        responses={
            200: "successfully got review record(s)",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.ReviewSchema(many=True))
    @jwtext.jwt_required()
    def get(self, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()
        reviews = current_user.reviews
        result = [_convert_review_v2_into_v1(review, fields) for review in reviews]
        return result

    @bp.doc(
        summary="create new review",
        responses={200: "review was created"},
        security="TokenAuth",
    )
    @bp.input(schemas.ReviewSchema, location="json")
    @bp.output(schemas.ReviewSchema)
    @jwtext.jwt_required()
    def post(self, json_data):
        current_user = jwtext.get_current_user()
        name = json_data.pop("name")
        # HACK: convert from v1 to v2 review schema here
        if "num_citation_screening_reviewers" in json_data:
            json_data["citation_reviewer_num_pcts"] = [
                {
                    "num": json_data.pop("num_citation_screening_reviewers"),
                    "pct": 100,
                }
            ]
        if "num_fulltext_screening_reviewers" in json_data:
            json_data["fulltext_reviewer_num_pcts"] = [
                {
                    "num": json_data.pop("num_fulltext_screening_reviewers"),
                    "pct": 100,
                }
            ]
        review = models.Review(name=name, **json_data)  # type: ignore
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
            os.path.join(
                current_app.config["CITATION_UPLOADS_DIR"], f"review_{review.id:08}"
            ),
            os.path.join(
                current_app.config["RANKER_MODELS_DIR"], f"review_{review.id:08}"
            ),
        ]
        for dirname in dirnames:
            try:
                os.makedirs(dirname, exist_ok=True)
            except OSError:
                pass  # TODO: fix this / the entire system for saving files to disk
        return _convert_review_v2_into_v1(review)


bp.add_url_rule("/<int:id>", view_func=ReviewAPI.as_view("review"))
bp.add_url_rule("/", view_func=ReviewsAPI.as_view("reviews"))


def _convert_review_v2_into_v1(
    review: models.Review, fields: t.Optional[list[str]] = None
) -> dict:
    record = schemas.ReviewV2Schema(only=fields).dump(review)
    assert isinstance(record, dict)  # type guard
    if record.get("citation_reviewer_num_pcts"):
        record["num_citation_screening_reviewers"] = record.pop(
            "citation_reviewer_num_pcts"
        )[0]["num"]
    if record.get("fulltext_reviewer_num_pcts"):
        record["num_fulltext_screening_reviewers"] = record.pop(
            "fulltext_reviewer_num_pcts"
        )[0]["num"]
    for field in ("created_at", "updated_at"):
        if field in record:
            record[field] = datetime.datetime.fromisoformat(record[field])
    return record
