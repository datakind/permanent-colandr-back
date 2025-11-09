import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from .. import errors, schemas


bp = af.APIBlueprint("citations", __name__, url_prefix="/citations")


class CitationAPI(MethodView):
    @bp.doc(
        summary="get a single citation",
        responses={
            200: "successfully got citation",
            403: "current app user forbidden to get citation",
            404: "no citation matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.CitationSchema)
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
                message=f"{current_user} forbidden to get this citation"
            )

        current_app.logger.debug("%s got %s citation", current_user, study)
        citation = _make_pseudo_citation_record(study)
        return (
            {key: val for key, val in citation.items() if key in fields}
            if fields
            else citation
        )

    @bp.doc(
        summary="modify a single citation",
        responses={
            200: "citation data was modified",
            403: "current app user forbidden to modify citation",
            404: "no citation matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.CitationSchema(partial=True), location="json")
    @bp.output(schemas.CitationSchema)
    @jwtext.jwt_required()
    def put(self, id, json_data):
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
                message=f"{current_user} forbidden to modify this study"
            )

        citation = study.citation | json_data
        study.citation = citation
        db.session.commit()

        current_app.logger.info("%s modified %s", current_user, study)
        citation = _make_pseudo_citation_record(study)
        return citation

    @bp.doc(
        summary="delete a single citation",
        responses={
            204: "successfully deleted citation record",
            403: "current app user forbidden to delete citation record",
            404: "no citation with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.output({}, status_code=204)
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
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete this study.citation"
            )

        study.citation = {}
        # to preserve previous behavior, we now have to manually delete associated screenings
        stmt = (
            sa.delete(models.Screening)
            .where(models.Screening.study_id == id)
            .where(models.Screening.stage == "citation")
        )
        db.session.execute(stmt)
        db.session.commit()

        current_app.logger.info("%s deleted %s citation", current_user, study)
        return ""


class CitationsPostSchema(schemas.DataSourceSchema):
    review_id = af.fields.Integer(
        required=True,
        validate=af.validators.Range(min=1),
        description="unique identifier for review for which citation will be created",
    )
    status = af.fields.String(
        validate=af.validators.OneOf(["not_screened", "included", "excluded"]),
        description="known screening status of citation, if anything",
    )


class CitationsAPI(MethodView):
    @bp.doc(
        summary="create a single citation",
        responses={
            200: "successfully created citation record",
            403: "current app user forbidden to create citation for this review",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.CitationSchema(partial=True), location="json")
    @bp.input(CitationsPostSchema, location="query")
    @jwtext.jwt_required()
    def post(self, json_data, query_data):
        review_id = query_data["review_id"]
        source_type = query_data["source_type"]
        source_name = query_data.get("source_name")
        source_url = query_data.get("source_url")
        status = query_data["status"]
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, review_id)

        current_app.logger.warning("json_data = %s", json_data)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        if (
            current_user.is_admin is False
            and db.session.execute(
                current_user.review_user_assoc.select().filter_by(review_id=review_id)
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to add citations to this review"
            )

        data_source = db.session.execute(
            sa.select(models.DataSource).filter_by(
                source_type=source_type, source_name=source_name
            )
        ).scalar_one_or_none()
        if data_source is None:
            data_source = models.DataSource(
                source_type=source_type, source_name=source_name, source_url=source_url
            )  # type: ignore
            db.session.add(data_source)
        db.session.commit()
        current_app.logger.info("%s inserted %s", current_user, data_source)

        # add the study w/ citation
        # citation = schemas.CitationSchema().load(json_data)
        study = models.Study(
            user_id=current_user.id,
            review_id=review_id,
            data_source_id=data_source.id,
            # citation=citation,
            citation=json_data,
        )  # type: ignore
        if status is not None:
            study.citation_status = status
        db.session.add(study)
        db.session.commit()
        current_app.logger.info("%s inserted %s", current_user, study)

        # TODO: what about deduplication?!
        # TODO: what about adding *multiple* citations via this endpoint?

        citation = _make_pseudo_citation_record(study)
        return citation


bp.add_url_rule("/<int:id>", view_func=CitationAPI.as_view("citation"))
bp.add_url_rule("/", view_func=CitationsAPI.as_view("citations"))


def _make_pseudo_citation_record(study: models.Study) -> dict:
    # pretend that citations are still separate records for api consistency
    citation = study.citation
    if citation:
        citation |= {
            "id": study.id,
            "review_id": study.review_id,
            "created_at": study.created_at,
            "updated_at": study.updated_at,
        }
    return citation
