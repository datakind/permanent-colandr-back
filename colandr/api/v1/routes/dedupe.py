import apiflask as af
import flask_jwt_extended as jwtext
from flask import current_app
from flask.views import MethodView

from .... import models, tasks
from ....extensions import db, limiter
from .. import authz, errors


bp = af.APIBlueprint("deduplicate studies", __name__, url_prefix="/dedupe")


class DedupeAPI(MethodView):
    @bp.doc(
        summary="deduplicate studies for a review",
        responses={
            403: "current app user forbidden to dedupe studies for this review",
            404: "no review matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "review_id": af.fields.Integer(
                required=True,
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier for review whose studies are to be deduplicated"
                },
            )
        },
        location="query",
    )
    @bp.output({})
    @jwtext.jwt_required()
    def post(self, query_data):
        review_id = query_data["review_id"]
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(
            current_user, review_id, if_frozen=False
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to dedupe studies for this review"
            )

        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        current_app.logger.info(
            "%s submitting deduplicate citations job for %s", current_user, review
        )
        tasks.deduplicate_citations.apply_async(args=[review_id], countdown=3)


# NOTE: flask-limiter doesn't behave when applied to routes via MethodView.decorators
# this is an ugly but serviceable work-around
dedupe_api_view_func = DedupeAPI.as_view("dedupe")
dedupe_api_view_func = limiter.limit("1 per 5 seconds")(dedupe_api_view_func)
bp.add_url_rule("/", view_func=dedupe_api_view_func)
