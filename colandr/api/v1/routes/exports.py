import collections
import csv
import itertools
import typing as t

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
import sqlalchemy.orm as sa_orm
from flask import Response, current_app, make_response, stream_with_context
from flask.views import MethodView

from .... import models
from ....extensions import db, limiter
from ....lib import fileio
from .. import authz, errors


bp = af.APIBlueprint("exports", __name__, url_prefix="/export")


class ExportStudiesAPI(MethodView):
    @bp.doc(
        summary="export studies data",
        responses={
            200: "successfully got studies data for specified review",
            403: "current app user forbidden to export studies data for specified review",
            404: "no review matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "review_id": af.fields.Integer(
                required=True, validate=af.validators.Range(min=1)
            ),
            "content_type": af.fields.String(
                load_default="text/csv", validate=af.validators.OneOf(["text/csv"])
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, query_data):
        review_id = query_data["review_id"]
        content_type = query_data["content_type"]
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to export data for this review"
            )

        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

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

        stmt = (
            sa.select(models.Study)
            .filter_by(review_id=review_id)
            .options(
                sa_orm.joinedload(models.Study.data_source),
                sa_orm.joinedload(models.Study.data_extraction),
            )
            .order_by(models.Study.id)
        )
        studies = db.session.execute(stmt).scalars().yield_per(1000)
        rows = (_study_to_row(study, extraction_label_types) for study in studies)
        if content_type == "text/csv":
            export_data = fileio.tabular.write_stream(
                fieldnames, rows, quoting=csv.QUOTE_NONNUMERIC
            )
        else:
            # NOTE: this can't happen owing to input schema validation
            raise NotImplementedError("only 'text/csv' content type is available")

        response = Response(
            stream_with_context(export_data),
            status=200,
            headers={
                "Content-Type": content_type,
                "Content-Disposition": "attachment; filename=colandr-review-studies.csv",
            },
        )
        current_app.logger.info("%s exported studies data for %s", current_user, review)
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


class ExportScreeningsAPI(MethodView):
    @bp.doc(
        summary="export screenings data",
        responses={
            200: "successfully got screenings data for specified review",
            403: "current app user forbidden to export screenings data for specified review",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "review_id": af.fields.Integer(
                required=True, validate=af.validators.Range(min=1)
            ),
            "content_type": af.fields.String(
                load_default="text/csv", validate=af.validators.OneOf(["text/csv"])
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, query_data):
        review_id = query_data["review_id"]
        content_type = query_data["content_type"]
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to export data for this review"
            )

        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

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
        # rows = (_screening_to_row(screening) for screening in screenings)
        rows = [_screening_to_row(screening) for screening in screenings]
        if content_type == "text/csv":
            export_data = fileio.tabular.write_stream(
                fieldnames, rows, quoting=csv.QUOTE_NONNUMERIC
            )
        else:
            # NOTE: this can't happen owing to input schema validation
            raise NotImplementedError("only 'text/csv' content type is available")

        response = make_response(export_data, 200)
        response.headers.update(
            {
                "Content-Type": content_type,
                "Content-Disposition": "attachment; filename=colandr-review-screenings.csv",
            }
        )
        current_app.logger.info(
            "%s exported screenings data for %s", current_user, review
        )
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


# TODO: this endpoint doesn't _really_ make sense here; consider moving / refactoring?
class ExportPrismaAPI(MethodView):
    @bp.doc(
        summary="export review PRISMA stats",
        responses={
            200: "successfully got review prisma data",
            403: "current app user forbidden to export review prisma data",
            404: "no review matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "review_id": af.fields.Integer(
                required=True, validate=af.validators.Range(min=1)
            )
        },
        location="query",
    )
    @bp.output(
        {
            "num_studies": af.fields.Integer(),
            "num_studies_by_source": af.fields.Dict(
                keys=af.fields.String(), values=af.fields.Integer()
            ),
            "num_unique_studies": af.fields.Integer(),
            "num_screened_citations": af.fields.Integer(),
            "num_excluded_citations": af.fields.Integer(),
            "num_screened_fulltexts": af.fields.Integer(),
            "num_excluded_fulltexts": af.fields.Integer(),
            "exclude_reason_counts": af.fields.Dict(
                keys=af.fields.String(), values=af.fields.Integer()
            ),
            "num_studies_data_extracted": af.fields.Integer(),
        }
    )
    @jwtext.jwt_required()
    def get(self, query_data):
        review_id = query_data["review_id"]
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to export data for this review"
            )

        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        # get counts by step, i.e. prisma
        n_studies_by_source_stmt = (
            sa.select(
                models.DataSource.source_type, db.func.sum(models.Import.num_records)
            )
            .filter(models.Import.data_source_id == models.DataSource.id)
            .filter(models.Import.review_id == review_id)
            .group_by(models.DataSource.source_type)
        )
        n_studies_by_source = {
            row.source_type: row.sum
            for row in db.session.execute(n_studies_by_source_stmt)
        }
        n_studies = sum(n_studies_by_source.values())

        n_unique_studies = db.session.execute(
            sa.select(sa.func.count()).select_from(
                sa.select(models.Study)
                .filter_by(review_id=review_id, dedupe_status="not_duplicate")
                .subquery()
            )
        ).scalar_one()

        n_citations_by_status_stmt = (
            sa.select(models.Study.citation_status, sa.func.count())
            .filter(models.Study.review_id == review_id)
            .filter(models.Study.citation_status.in_(["included", "excluded"]))
            .group_by(models.Study.citation_status)
        )
        n_citations_by_status = {
            row.citation_status: row.count
            for row in db.session.execute(n_citations_by_status_stmt)
        }
        n_citations_screened = sum(n_citations_by_status.values())
        n_citations_excluded = n_citations_by_status.get("excluded", 0)

        n_fulltexts_by_status_stmt = (
            sa.select(models.Study.fulltext_status, sa.func.count())
            .filter(models.Study.review_id == review_id)
            .filter(models.Study.fulltext_status.in_(["included", "excluded"]))
            .group_by(models.Study.fulltext_status)
        )
        n_fulltexts_by_status = {
            row.fulltext_status: row.count
            for row in db.session.execute(n_fulltexts_by_status_stmt)
        }
        n_fulltexts_screened = sum(n_fulltexts_by_status.values())
        n_fulltexts_excluded = n_fulltexts_by_status.get("excluded", 0)

        results = db.session.execute(
            sa.select(models.Screening.exclude_reasons).filter_by(review_id=review_id)
        ).all()
        exclude_reason_counts = dict(
            collections.Counter(
                itertools.chain.from_iterable(
                    [result[0] for result in results if result[0] is not None]
                )
            )
        )
        n_data_extractions = db.session.execute(
            sa.select(sa.func.count()).select_from(
                sa.select(models.Study)
                .filter_by(review_id=review_id, data_extraction_status="finished")
                .subquery()
            )
        ).scalar_one()

        current_app.logger.debug(
            "%s exported PRISMA stats for %s", current_user, review
        )
        return {
            "num_studies": n_studies,
            "num_studies_by_source": n_studies_by_source,
            "num_unique_studies": n_unique_studies,
            "num_screened_citations": n_citations_screened,
            "num_excluded_citations": n_citations_excluded,
            "num_screened_fulltexts": n_fulltexts_screened,
            "num_excluded_fulltexts": n_fulltexts_excluded,
            "exclude_reason_counts": exclude_reason_counts,
            "num_studies_data_extracted": n_data_extractions,
        }


bp.add_url_rule("/studies", view_func=ExportStudiesAPI.as_view("studies"))
bp.add_url_rule("/screenings", view_func=ExportScreeningsAPI.as_view("screenings"))
bp.add_url_rule("/prisma", view_func=ExportPrismaAPI.as_view("prisma"))
limiter.limit("1 per 5 seconds")(bp)
