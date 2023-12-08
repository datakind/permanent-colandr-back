import warnings

import flask_jwt_extended as jwtext
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...extensions import db
from ...lib import constants
from ...models import Review
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import ReviewPlanSchema
from ..swagger import review_plan_model


ns = Namespace(
    "review_plans",
    path="/reviews/<int:id>/plan",
    description="get, delete, update review plans",
)


@ns.route("")
@ns.doc(
    summary="get, delete, update review plans",
    produces=["application/json"],
)
class ReviewPlanResource(Resource):
    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of review fields to return",
            },
        },
        responses={
            200: "successfully got review plan record",
            403: "current app user forbidden to get review plan record",
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
        """get review plan record for a single review by id"""
        current_user = jwtext.get_current_user()
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        if (
            current_user.is_admin is False
            and review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(f"{current_user} forbidden to get this review plan")
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", review.review_plan)
        return ReviewPlanSchema(only=fields).dump(review.review_plan)

    @ns.doc(
        description='Since review plans are created automatically upon review creation and deleted automatically upon review deletion, "delete" here amounts to nulling out some or all of its non-required fields',
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": 'comma-delimited list-as-string of review fields to "delete" (set to null)',
            },
        },
        responses={
            204: "successfully deleted (nulled) review plan record",
            403: "current app user forbidden to delete review plan record",
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
            "fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None),
        },
        location="query",
    )
    @jwtext.jwt_required(fresh=True)
    def delete(self, id, fields):
        """delete review plan record for a single review by id"""
        current_user = jwtext.get_current_user()
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        if current_user.is_admin is False and current_user not in review.owners:
            return forbidden_error(
                f"{current_user} forbidden to delete this review plan"
            )
        review_plan = review.review_plan
        if fields:
            for field in fields:
                if field == "objective":
                    review_plan.objective = ""
                elif field == "pico":
                    review_plan.pico = {}
                else:
                    setattr(review_plan, field, [])
        else:
            review_plan.objective = ""
            review_plan.research_questions = []
            review_plan.pico = {}
            review_plan.keyterms = []
            review_plan.selection_criteria = []
            review_plan.data_extraction_form = []
        db.session.commit()
        current_app.logger.info("deleted contents of %s", review_plan)
        return "", 204

    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "[DEPRECATED] comma-delimited list-as-string of review fields to modify",
            },
        },
        expect=(review_plan_model, "review plan data to be modified"),
        responses={
            200: "review plan data was modified",
            403: "current app user forbidden to modify review plan",
            404: "no review with matching id was found",
        },
    )
    @use_args(ReviewPlanSchema(partial=True), location="json")
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
            "fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def put(self, args, id, fields):
        """modify review plan record for a single review by id"""
        current_user = jwtext.get_current_user()
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        if current_user.is_admin is False and current_user not in review.owners:
            return forbidden_error(
                f"{current_user} forbidden to create this review plan"
            )
        review_plan = review.review_plan
        if not review_plan:
            return not_found_error(f"<ReviewPlan(review_id={id})> not found")
        if fields:
            with warnings.catch_warnings():
                warnings.simplefilter("always", DeprecationWarning)
                warnings.warn(
                    '"fields" param in ReviewPlanResource.put is no longer needed',
                    category=DeprecationWarning,
                )
            for field in fields:
                try:
                    setattr(review_plan, field, args[field])
                except KeyError:
                    return bad_request_error(f'field "{field}" value not specified')
        else:
            for key, value in args.items():
                setattr(review_plan, key, value)

        db.session.commit()
        current_app.logger.info("modified contents of %s", review_plan)
        return ReviewPlanSchema().dump(review_plan)
