import csv
import itertools
import typing as t

import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app, make_response
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants, fileio
from ..errors import forbidden_error, not_found_error


ns = Namespace("exports", path="/export", description="export data")


@ns.route("/studies")
@ns.doc(summary="export studies data")
class ExportStudiesResource(Resource):
    @ns.doc(
        description="export studies data",
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
            },
            "content_type": {
                "in": "query",
                "type": "string",
            },
        },
        responses={
            200: "successfully got studies data for specified review",
            403: "current app user forbidden to export studies data for specified review",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "content_type": ma_fields.String(
                load_default="text/csv", validate=OneOf(["text/csv"])
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, review_id, content_type):
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
            return forbidden_error(f"{current_user} forbidden to get this review")

        fieldnames = [
            "study_id",
            "study_tags",
            "deduplication_status",
            "citation_screening_status",
            "fulltext_screening_status",
            "data_extraction_screening_status",
            "data_source_type",
            "data_source_name",
            "data_source_url",
            "citation_title",
            "citation_abstract",
            "citation_authors",
            "citation_journal_name",
            "citation_journal_volume",
            "citation_pub_year",
            "citation_keywords",
            "citation_exclude_reasons",
            "fulltext_filename",
            "fulltext_exclude_reasons",
        ]
        extraction_label_types: t.Optional[list[tuple[str, str]]]
        data_extraction_form = db.session.execute(
            sa.select(models.ReviewPlan.data_extraction_form).filter_by(id=review_id)
        ).one_or_none()
        if data_extraction_form:
            extraction_label_types = [
                (item["label"], item["field_type"]) for item in data_extraction_form[0]
            ]
            fieldnames.extend(label for label, _ in extraction_label_types)
        else:
            extraction_label_types = None

        # TODO: make this query performant and fully streamable, even with lazy-loading
        # see: https://docs.sqlalchemy.org/en/14/errors.html#parent-instance-x-is-not-bound-to-a-session-lazy-load-deferred-load-refresh-etc-operation-cannot-proceed
        # see: https://docs.sqlalchemy.org/en/14/errors.html#object-cannot-be-converted-to-persistent-state-as-this-identity-map-is-no-longer-valid
        studies = db.session.execute(
            sa.select(models.Study)
            .filter_by(review_id=review_id)
            .order_by(models.Study.id),
            execution_options={"prebuffer_rows": True},
        ).scalars()
        # rows = (_study_to_row(study, extraction_label_types) for study in studies)
        rows = [_study_to_row(study, extraction_label_types) for study in studies]
        if content_type == "text/csv":
            export_data = fileio.tabular.write_stream(
                fieldnames, rows, quoting=csv.QUOTE_NONNUMERIC
            )
        else:
            raise NotImplementedError("only 'text/csv' content type is available")

        response = make_response(export_data, 200)
        response.headers.update(
            {
                "Content-Type": content_type,
                "Content-Disposition": "attachment; filename=colandr-review-studies.csv",
            }
        )
        current_app.logger.info("studies data exported for %s", review)
        return response


def _study_to_row(
    study: models.Study, extraction_label_types: t.Optional[list[tuple[str, str]]]
) -> dict:
    row = {
        "study_id": study.id,
        "study_tags": "; ".join(study.tags) if study.tags else None,
        "deduplication_status": study.dedupe_status,
        "citation_screening_status": study.citation_status,
        "fulltext_screening_status": study.fulltext_status,
        "data_extraction_screening_status": study.data_extraction_status,
        "data_source_type": study.data_source.source_type,
        "data_source_name": study.data_source.source_name,
        "data_source_url": study.data_source.source_url,
    }
    if study.citation:
        citation = study.citation
        row.update(
            {
                "citation_title": citation.get("title"),
                "citation_abstract": citation.get("abstract"),
                "citation_authors": (
                    "; ".join(citation["authors"]) if citation.get("authors") else None
                ),
                "citation_journal_name": citation.get("journal_name"),
                "citation_journal_volume": citation.get("volume"),
                "citation_pub_year": citation.get("pub_year"),
                "citation_keywords": (
                    "; ".join(citation["keywords"])
                    if citation.get("keywords")
                    else None
                ),
                "citation_exclude_reasons": (
                    "; ".join(study.citation_exclude_reasons)
                    if study.citation_exclude_reasons
                    else None
                ),
            }
        )
    if study.fulltext:
        fulltext = study.fulltext
        row.update(
            {
                "fulltext_filename": fulltext.get("original_filename"),
                "fulltext_exclude_reasons": (
                    "; ".join(study.fulltext_exclude_reasons)
                    if study.fulltext_exclude_reasons
                    else None
                ),
            }
        )
    if extraction_label_types and study.data_extraction:
        extracted_data = {
            item["label"]: item["value"]
            for item in study.data_extraction.extracted_items
        }
        row.update(
            {
                label: (
                    "; ".join(extracted_data.get(label, []))
                    if type_ in ("select_one", "select_many")
                    else extracted_data.get(label, None)
                )
                for label, type_ in extraction_label_types
            }
        )
    return row


@ns.route("/screenings")
@ns.doc(summary="export screenings data")
class ExportScreeningsResource(Resource):
    @ns.doc(
        description="export screenings data",
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
            },
        },
        responses={
            200: "successfully got screenings data for specified review",
            403: "current app user forbidden to export screenings data for specified review",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "content_type": ma_fields.String(
                load_default="text/csv", validate=OneOf(["text/csv"])
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, review_id, content_type):
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
            return forbidden_error(f"{current_user} forbidden to get this review")

        screenings = db.session.execute(
            sa.select(models.Screening)
            .filter_by(review_id=review_id)
            .order_by(models.Screening.id)
        ).scalars()
        fieldnames = [
            "study_id",
            "screening_stage",
            "screening_status",
            "screening_exclude_reasons",
            "user_email",
            "user_name",
        ]
        rows = (_screening_to_row(screening) for screening in screenings)
        if content_type == "text/csv":
            export_data = fileio.tabular.write_stream(
                fieldnames, rows, quoting=csv.QUOTE_NONNUMERIC
            )
        else:
            raise NotImplementedError("only 'text/csv' content type is available")

        response = make_response(export_data, 200)
        response.headers["Content-type"] = content_type
        current_app.logger.info("screenings data exported for %s", review)

        return response


def _screening_to_row(screening: models.Screening) -> dict:
    row = {
        "study_id": screening.study_id,
        "screening_stage": screening.stage,
        "screening_status": screening.status,
        "screening_exclude_reasons": screening.exclude_reasons,
    }
    user = screening.user
    if user:
        row.update({"user_email": user.email, "user_name": user.name})
    return row
