import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from .. import errors, schemas


bp = af.APIBlueprint("fulltexts", __name__, url_prefix="/fulltexts")


class FulltextAPI(MethodView):
    @bp.doc(
        summary="get a single fulltext",
        responses={
            200: "successfully got fulltext",
            403: "current app user forbidden to get fulltext",
            404: "no fulltext matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.FulltextSchema)
    @jwtext.jwt_required()
    def get(self, id, query_data):
        fields = query_data.get("fields_")
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
                message=f"{current_user} forbidden to get this fulltext"
            )

        current_app.logger.debug("got %s", study)
        fulltext = _make_pseudo_fulltext_record(study)
        return (
            {key: val for key, val in fulltext.items() if key in fields}
            if fields
            else fulltext
        )

    @bp.doc(
        summary="delete a single fulltext",
        responses={
            204: "successfully deleted fulltext",
            403: "current app user forbidden to delete fulltext",
            404: "no fulltext matching id was found",
        },
        security="TokenAuth",
    )
    @bp.output({}, 204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
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
        ) or study.review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete this study.fulltext"
            )

        study.fulltext = {}
        # to preserve previous behavior, we now have to manually delete associated screenings
        stmt = (
            sa.delete(models.Screening)
            .where(models.Screening.study_id == id)
            .where(models.Screening.stage == "fulltext")
        )
        db.session.execute(stmt)
        db.session.commit()
        current_app.logger.info("%s deleted %s fulltext", current_user, study)
        return ""


def _make_pseudo_fulltext_record(study: models.Study) -> dict:
    # pretend that fulltexts are still separate records for api consistency
    fulltext = study.fulltext
    if fulltext:
        fulltext |= {
            "id": study.id,
            "review_id": study.review_id,
            "created_at": study.created_at,
            "updated_at": study.updated_at,
        }
    return fulltext


bp.add_url_rule("/<int:id>", view_func=FulltextAPI.as_view("fulltext"))
