import apiflask as af
import flask_jwt_extended as jwtext
from flask.views import MethodView

from .... import models
from ....extensions import db
from ....lib.extractors.locations import get_locations
from .. import errors, schemas


bp = af.APIBlueprint("fulltext locations", __name__, url_prefix="/fulltexts")


class FulltextLocationsAPI(MethodView):
    @bp.doc(
        summary="extract locations from fulltext content",
        responses={
            200: "successfully extracted locations from fulltext",
            403: "current app user forbidden to access this fulltext",
            404: "no fulltext with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.output(schemas.MetadataSchema(many=True))
    @jwtext.jwt_required()
    def get(self, id):
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if (
            current_user.is_admin is False
            and study.review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to access this fulltext"
            )

        locations = (
            []
            if not study.fulltext or not study.fulltext.get("text_content")
            else get_locations(study.id, study.fulltext.get("text_content", ""))
        )

        return locations


bp.add_url_rule(
    "/<int:id>/locations", view_func=FulltextLocationsAPI.as_view("fulltext_locations")
)
