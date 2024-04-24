import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants
from ..errors import forbidden_error, not_found_error
from ..schemas import FulltextSchema


ns = Namespace("fulltexts", path="/fulltexts", description="get and delete fulltexts")


@ns.route("/<int:id>")
@ns.doc(
    summary="get and delete fulltexts",
    produces=["application/json"],
)
class FulltextResource(Resource):
    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of fulltext fields to return",
            },
        },
        responses={
            200: "successfully got fulltext record",
            403: "current app user forbidden to get fulltext record",
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
    @use_kwargs(
        {"fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None)},
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, id, fields):
        """get record for a single fulltext by id"""
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
            return forbidden_error(f"{current_user} forbidden to get this fulltext")
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", study)
        fulltext = _make_pseudo_fulltext_record(study)
        return FulltextSchema(only=fields).dump(fulltext)

    @ns.doc(
        responses={
            204: "successfully deleted fulltext record",
            403: "current app user forbidden to delete fulltext record",
            404: "no fulltext with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        """delete record for a single fulltext by id"""
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
            return forbidden_error(
                f"{current_user} forbidden to delete this study.fulltext"
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
        current_app.logger.info("deleted %s fulltext", study)
        return "", 204


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
