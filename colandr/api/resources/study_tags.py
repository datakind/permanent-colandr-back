import itertools

import flask_praetorian
from flask import current_app, g
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ...extensions import db
from ...lib import constants
from ...models import Review, Study
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
    method_decorators = [flask_praetorian.auth_required]

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
        location="view_args",
    )
    def get(self, review_id):
        """get all distinct tags assigned to studies"""
        current_user = flask_praetorian.current_user()
        review = db.session.get(Review, review_id)
        if not review:
            return not_found_error(f"<Review(id={review_id})> not found")
        if (
            current_user.is_admin is False
            and review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to get study tags for this review"
            )
        studies = review.studies.filter(Study.tags != []).with_entities(Study.tags)
        current_app.logger.debug("got tags for %s", review)
        return sorted(set(itertools.chain.from_iterable(study[0] for study in studies)))
