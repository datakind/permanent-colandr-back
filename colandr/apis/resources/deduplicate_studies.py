import flask_jwt_extended as jwtext
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ... import models, tasks
from ...extensions import db
from ...lib import constants
from ..errors import forbidden_error, not_found_error


ns = Namespace(
    "deduplicate_studies",
    path="/dedupe",
    description="manually trigger deduplication of studies",
)


@ns.route("")
@ns.doc(
    summary="manually trigger deduplication of studies",
    produces=["application/json"],
)
class DeduplicateStudiesResource(Resource):
    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier for review whose studies are to be deduplicated",
            },
        },
        responses={
            403: "current app user forbidden to dedupe studies for this review",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def post(self, review_id):
        """get all distinct tags assigned to studies"""
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, review_id)
        if not review:
            return not_found_error(f"<Review(id={review_id})> not found")
        if (
            current_user.is_admin is False
            and review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to dedupe studies for this review"
            )
        tasks.deduplicate_citations.apply_async(args=[review_id], countdown=3)
