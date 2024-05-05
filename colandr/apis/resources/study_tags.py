import itertools

import flask_jwt_extended as jwtext
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants
from ..errors import forbidden_error, not_found_error


ns = Namespace(
    "study_tags",
    path="/studies/tags",
    description="get all distinct tags assigned to studies",
)


@ns.route("")
@ns.doc(
    summary="get all distinct tags assigned to studies",
    produces=["application/json"],
)
class StudyTagsResource(Resource):
    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier for review whose tags are to be fetched",
            },
        },
        responses={
            200: "successfully got study tags",
            403: "current app user forbidden to get study tags for this review",
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
    def get(self, review_id):
        """get all distinct tags assigned to studies"""
        current_user = jwtext.get_current_user()
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
                f"{current_user} forbidden to get study tags for this review"
            )
        studies = db.session.execute(
            review.studies.select()
            .filter(models.Study.tags != [])
            .with_only_columns(models.Study.tags)
        )
        current_app.logger.debug("got tags for %s", review)
        return sorted(set(itertools.chain.from_iterable(study[0] for study in studies)))
