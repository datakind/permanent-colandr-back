import flask_jwt_extended as jwtext
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants
from ...lib.extractors.locations import get_locations
from ..errors import forbidden_error, not_found_error
from ..schemas import MetadataSchema


ns = Namespace("fulltext_locations", path="/fulltexts", description="get fulltext locations")


@ns.route("/<int:id>/locations")
@ns.doc(
    summary="extract locations from fulltext",
    produces=["application/json"],
)
class FulltextLocationsResource(Resource):
    @ns.doc(
        responses={
            200: "successfully extracted locations from fulltext",
            403: "current app user forbidden to access this fulltext",
            404: "no fulltext with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            )
        },
        location="view_args",
    )
    @jwtext.jwt_required()
    def get(self, id):
        """Extract locations from the fulltext content"""
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)
        if not study:
            return not_found_error(f"<Study(id={id})> not found")
        if (
            current_user.is_admin is False
            and study.review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            return forbidden_error(f"{current_user} forbidden to access this fulltext")

        if not study.fulltext or not study.fulltext.get("text_content"):
            return [], 200

        locations = get_locations(study.id, study.fulltext.get("text_content", ""))

        return MetadataSchema(many=True).dump(locations)
