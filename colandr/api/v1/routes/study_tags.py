import itertools

import apiflask as af
import flask_jwt_extended as jwtext
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from .. import errors


bp = af.APIBlueprint("study_tags", __name__, url_prefix="/studies/tags")


class StudyTagsAPI(MethodView):
    @bp.doc(
        summary="get all distinct tags assigned to studies",
        responses={
            200: "successfully got study tags",
            403: "current app user forbidden to get study tags for this review",
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
    # TODO: see TODO below
    # @bp.output({})
    @jwtext.jwt_required()
    def get(self, query_data):
        review_id = query_data["review_id"]
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, review_id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        if (
            current_user.is_admin is False
            and review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get study tags for this review"
            )

        studies = db.session.execute(
            review.studies.select()
            .filter(models.Study.tags != [])
            .with_only_columns(models.Study.tags)
        )

        current_app.logger.debug("%s got study tags for %s", current_user, review)
        # TODO: pretty gross to return a bare list[str] from a JSON API
        # should probably be structured like [{"tag": TAG1}, {"tag": TAG2}, ...]
        return sorted(set(itertools.chain.from_iterable(study[0] for study in studies)))


bp.add_url_rule("/", view_func=StudyTagsAPI.as_view("study_tags"))
