import apiflask as af
import flask_jwt_extended as jwtext
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from .. import errors, schemas


# TODO: improve this routing for v2 API
bp = af.APIBlueprint("review_plans", __name__, url_prefix="/reviews/<int:id>/plan")


class ReviewPlanAPI(MethodView):
    @bp.doc(
        summary="get a single review plan",
        responses={
            200: "successfully got review plan",
            403: "current app user forbidden to get review plan",
            404: "no review plan matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.ReviewPlanSchema)
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
                message=f"{current_user} forbidden to get this review plan"
            )

        return models.model_to_dict(review.review_plan, fields)

    @bp.doc(
        summary="delete a single review plan",
        responses={
            204: "successfully deleted review plan",
            403: "current app user forbidden to delete review plan",
            404: "no review plan matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output({}, status_code=204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        if (
            current_user.is_admin is False and current_user not in review.owners
        ) or review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete this review plan"
            )

        review_plan = review.review_plan
        if fields:
            for field in fields:
                if field == "objective":
                    review_plan.objective = ""
                elif field.startswith("pico"):
                    if field == "pico":
                        review_plan.pico = {}
                    else:
                        _, subfield = field.split(".")
                        review_plan.pico = {
                            key: val
                            for key, val in review_plan.pico.items()
                            if key != subfield
                        }
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
        return ""

    @bp.doc(
        summary="modify a single review plan",
        responses={
            200: "review plan data was modified",
            403: "current app user forbidden to modify review plan",
            404: "no review plan matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.ReviewPlanSchema(partial=True), location="json")
    @bp.output(schemas.ReviewPlanSchema)
    @jwtext.jwt_required()
    def put(self, id, json_data):
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        if (
            current_user.is_admin is False and current_user not in review.owners
        ) or review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to create this review plan"
            )

        review_plan = review.review_plan
        if not review_plan:
            raise errors.NotFoundError(
                message=f"<ReviewPlan(review_id={id})> not found"
            )

        for key, value in json_data.items():
            setattr(review_plan, key, value)
        db.session.commit()

        current_app.logger.info(
            "%s modified %s, attributes=%s",
            current_user,
            review_plan,
            sorted(json_data.keys()),
        )
        return review_plan


bp.add_url_rule("/", view_func=ReviewPlanAPI.as_view("review_plan"))
