import random
from operator import itemgetter

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from ....lib import constants
from ....lib.models import StudyRanker
from ....lib.nlp import reviewer_terms
from .. import errors, schemas


bp = af.APIBlueprint("studies", __name__, url_prefix="/studies")


class StudiesGetSchema(schemas.FieldsSchema):
    review_id = af.fields.Integer(
        required=True,
        validate=af.validators.Range(min=1, max=constants.MAX_INT),
        description="unique identifier for review whose studies are to be fetched",
    )
    dedupe_status = af.fields.String(
        validate=af.validators.OneOf(constants.DEDUPE_STATUSES),
        description="filter studies to only those with matching deduplication statuses",
    )
    citation_status = af.fields.String(
        validate=af.validators.OneOf(constants.USER_SCREENING_STATUSES),
        description="filter studies to only those with matching citation statuses",
    )
    fulltext_status = af.fields.String(
        validate=af.validators.OneOf(constants.USER_SCREENING_STATUSES),
        description="filter studies to only those with matching fulltext statuses",
    )
    data_extraction_status = af.fields.String(
        validate=af.validators.OneOf(constants.EXTRACTION_STATUSES),
        description="filter studies to only those with matching data extraction statuses",
    )
    num_citation_reviewers = af.fields.Integer(
        validate=af.validators.Range(min=1, max=3),
        description="filter studies to only those with a matching number of citation reviewers",
    )
    num_fulltext_reviewers = af.fields.Integer(
        validate=af.validators.Range(min=1, max=3),
        description="filter studies to only those with a matching number of fulltext reviewers",
    )
    tag = af.fields.String(
        validate=af.validators.Length(max=25),
        description="filter studies to only those with a matching (user-assigned) tag",
    )
    tsquery = af.fields.String(
        validate=af.validators.Length(max=50),
        description="filter studies to only those whose text content contains this word or phrase",
    )
    order_by = af.fields.String(
        load_default="relevance",
        validate=af.validators.OneOf(["recency", "relevance"]),
        description="order matching studies by either date imported or expected relevance (default: 'relevance')",
    )
    order_dir = af.fields.String(
        load_default="DESC",
        validate=af.validators.OneOf(["ASC", "DESC"]),
        description="direction of ordering, either in ascending or descending order (default: 'DESC')",
    )
    page = af.fields.Integer(
        load_default=0,
        validate=af.validators.Range(min=0),
        description="page number of the collection of ordered, matching studies, starting at 0",
    )
    per_page = af.fields.Integer(
        load_default=25,
        validate=af.validators.OneOf([1, 10, 25, 50, 100, 5000]),
        description="number of studies to include per page (default: 25)",
    )


class StudyAPI(MethodView):
    @bp.doc(
        summary="get a single study",
        responses={
            200: "successfully got study",
            403: "current app user forbidden to get study",
            404: "no study  matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.StudySchema)
    @jwtext.jwt_required()
    def get(self, id, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if not _is_allowed(current_user, study.review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get this study"
            )

        current_app.logger.debug("%s got %s", current_user, study)
        return models.model_to_dict(study, fields=fields)

    @bp.doc(
        summary="modify a single study",
        responses={
            200: "study data was modified",
            403: "current app user forbidden to modify study; specified field may not be modified",
            404: "no study with matching id was found",
        },
    )
    @bp.input(
        schemas.StudySchema(only=["data_extraction_status", "tags"]), location="json"
    )
    @bp.output(schemas.StudySchema)
    @jwtext.jwt_required()
    def put(self, id, json_data):
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if not _is_allowed(current_user, study.review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to modify this study"
            )

        for key, value in json_data.items():
            # TODO: should we have this check for fulltext_screening_status as well?
            if key == "data_extraction_status":
                if study.fulltext_status != "included":
                    raise errors.ForbiddenError(
                        message=f"<Study(id={id})> data_extraction_status can't be set "
                        "until fulltext has passed screening"
                    )
            setattr(study, key, value)
        db.session.commit()

        current_app.logger.info("%s modified %s", current_user, study)
        return study

    @bp.doc(
        summary="delete a single study",
        responses={
            204: "successfully deleted study record",
            403: "current app user forbidden to delete study record",
            404: "no study with matching id was found",
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

        if not _is_allowed(current_user, study.review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete this study"
            )

        db.session.delete(study)
        db.session.commit()
        current_app.logger.info("%s deleted %s", current_user, study)
        return ""


class StudiesAPI(MethodView):
    @bp.doc(
        summary="get studies matching filters",
        responses={
            200: "successfully got matching study record(s)",
            403: "current app user forbidden to get studies for this review",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(StudiesGetSchema, location="query")
    @bp.output(schemas.StudySchema(many=True))
    @jwtext.jwt_required()
    def get(self, query_data):
        fields = query_data.get("fields_")
        review_id = query_data["review_id"]
        dedupe_status = query_data.get("dedupe_status")
        citation_status = query_data.get("citation_status")
        fulltext_status = query_data.get("fulltext_status")
        data_extraction_status = query_data.get("data_extraction_status")
        num_citation_reviewers = query_data.get("num_citation_reviewers")
        num_fulltext_reviewers = query_data.get("num_fulltext_reviewers")
        tag = query_data.get("tag")
        tsquery = query_data.get("tsquery")
        order_by = query_data.get("order_by")
        order_dir = query_data.get("order_dir")
        page = query_data.get("page")
        per_page = query_data.get("per_page")
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, review_id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        if not _is_allowed(current_user, review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get studies from this review"
            )

        stmt = sa.select(models.Study).where(models.Study.review_id == review_id)

        if dedupe_status is not None:
            stmt = stmt.where(models.Study.dedupe_status == dedupe_status)
        if num_citation_reviewers is not None:
            stmt = stmt.where(
                models.Study.num_citation_reviewers == num_citation_reviewers
            )
        if num_fulltext_reviewers is not None:
            stmt = stmt.where(
                models.Study.num_fulltext_reviewers == num_fulltext_reviewers
            )
        if tag:
            stmt = stmt.where(models.Study.tags.any_() == tag)

        if citation_status is not None:
            if citation_status in {"conflict", "excluded", "included"}:
                stmt = stmt.where(models.Study.citation_status == citation_status)
            elif citation_status == "pending":
                user_screened_sq = (
                    sa.select(models.Screening.study_id).where(
                        models.Screening.stage == "citation",
                        models.Screening.user_id == current_user.id,
                    )
                ).subquery("user_screened")
                study_ids_sq = (
                    sa.select(models.Study.id)
                    .where(
                        models.Study.dedupe_status == "not_duplicate",
                        models.Study.citation_status.not_in(
                            ["included", "excluded", "conflict"]
                        ),
                    )
                    .join(
                        user_screened_sq,
                        models.Study.id == user_screened_sq.c.study_id,
                        isouter=True,
                    )
                ).where(
                    sa.or_(
                        models.Study.citation_status == "not_screened",
                        user_screened_sq.c.study_id == None,
                    )
                )
                stmt = stmt.where(models.Study.id.in_(study_ids_sq))
            elif citation_status == "awaiting_coscreener":
                user_screened_sq = (
                    sa.select(models.Screening.study_id).where(
                        models.Screening.stage == "citation",
                        models.Screening.user_id == current_user.id,
                    )
                ).subquery("user_screened")
                study_ids_sq = (
                    sa.select(models.Study.id)
                    .where(models.Study.citation_status == "screened_once")
                    .join(
                        user_screened_sq,
                        models.Study.id == user_screened_sq.c.study_id,
                        isouter=True,
                    )
                ).where(user_screened_sq.c.study_id != None)
                stmt = stmt.where(models.Study.id.in_(study_ids_sq))

        if fulltext_status is not None:
            if fulltext_status in {"conflict", "excluded", "included"}:
                stmt = stmt.where(models.Study.fulltext_status == fulltext_status)
            elif fulltext_status == "pending":
                user_screened_sq = (
                    sa.select(models.Screening.study_id).where(
                        models.Screening.stage == "fulltext",
                        models.Screening.user_id == current_user.id,
                    )
                ).subquery("user_screened")
                study_ids_sq = (
                    sa.select(models.Study.id)
                    .where(
                        models.Study.citation_status == "included",
                        models.Study.fulltext_status.not_in(
                            ["included", "excluded", "conflict"]
                        ),
                    )
                    .join(
                        user_screened_sq,
                        models.Study.id == user_screened_sq.c.study_id,
                        isouter=True,
                    )
                ).where(
                    sa.or_(
                        models.Study.fulltext_status == "not_screened",
                        user_screened_sq.c.study_id == None,
                    )
                )
                stmt = stmt.where(models.Study.id.in_(study_ids_sq))
            elif fulltext_status == "awaiting_coscreener":
                user_screened_sq = (
                    sa.select(models.Screening.study_id).where(
                        models.Screening.stage == "fulltext",
                        models.Screening.user_id == current_user.id,
                    )
                ).subquery("user_screened")
                study_ids_sq = (
                    sa.select(models.Study.id)
                    .where(models.Study.fulltext_status == "screened_once")
                    .join(
                        user_screened_sq,
                        models.Study.id == user_screened_sq.c.study_id,
                        isouter=True,
                    )
                ).where(user_screened_sq.c.study_id != None)
                stmt = stmt.where(models.Study.id.in_(study_ids_sq))

        if data_extraction_status is not None:
            if data_extraction_status == "not_started":
                stmt = stmt.where(
                    models.Study.fulltext_status == "included",  # this is necessary!
                    models.Study.data_extraction_status == data_extraction_status,
                )
            else:
                stmt = stmt.where(
                    models.Study.data_extraction_status == data_extraction_status
                )

        if tsquery and order_by != "relevance":  # HACK...
            stmt = stmt.where(models.Study.citation_text_content.match(tsquery))

        # order, offset, and limit
        if order_by == "recency":
            order_by = (
                sa.desc(models.Study.id)
                if order_dir == "DESC"
                else sa.asc(models.Study.id)
            )
            stmt = stmt.order_by(order_by)
            stmt = stmt.offset(page * per_page).limit(per_page)
            results = db.session.execute(stmt).scalars().all()

            current_app.logger.debug(
                "%s got %s studies for %s", current_user, len(results), review
            )
            return [models.model_to_dict(result, fields=fields) for result in results]

        elif order_by == "relevance":
            if tsquery:
                stmt = stmt.where(models.Study.citation_text_content.match(tsquery))

            # get results and corresponding relevance scores
            limit = 10 * per_page
            stmt = stmt.order_by(db.func.random()).limit(limit)
            results = db.session.execute(stmt).scalars().all()
            scores = None

            # best option: we have a trained study ranker model
            study_ranker = StudyRanker(
                review_id, current_app.config["RANKER_MODELS_DIR"]
            )
            if study_ranker.model_fpath.exists():
                records = (
                    {
                        "text": (
                            result.fulltext["text_content"][:5000]
                            if result.fulltext and result.fulltext.get("text_content")
                            else result.citation_text_content
                        )
                    }
                    for result in results
                )
                try:
                    scores = study_ranker.predict_many(records, proba=True)[True]
                except KeyError:  # no records, apparently
                    pass

            # # next best option: both positive and negative keyterms
            # if not scores:
            #     review_plan = review.review_plan
            #     suggested_keyterms = review_plan.suggested_keyterms
            #     if suggested_keyterms:
            #         incl_regex, excl_regex = reviewer_terms.get_incl_excl_terms_regex(
            #             review_plan.suggested_keyterms
            #         )
            #         scores = [
            #             reviewer_terms.get_incl_excl_terms_score(
            #                 incl_regex, excl_regex, result.citation_text_content
            #             )
            #             for result in results
            #         ]

            # # last option: just reviewer terms
            # if not scores:
            #     review_plan = review.review_plan
            #     keyterms = review_plan.keyterms
            #     if keyterms:
            #         keyterms_regex = reviewer_terms.get_keyterms_regex(keyterms)
            #         scores = [
            #             reviewer_terms.get_keyterms_score(
            #                 keyterms_regex, result.citation_text_content
            #             )
            #             for result in results
            #         ]

            # no model, let's just order results randomly...
            if scores is None:
                scores = list(range(len(results)))
                random.shuffle(scores)

            # zip the results and scores together, sort and offset accordingly
            sorted_results = [
                result
                for result, _ in sorted(
                    zip(results, scores),
                    key=itemgetter(1),
                    reverse=False if order_dir == "ASC" else True,
                )
            ]
            offset = page * per_page
            sorted_results = sorted_results[offset : offset + per_page]

            current_app.logger.debug(
                "%s got %s studies for %s", current_user, len(results), review
            )
            return [
                models.model_to_dict(result, fields=fields) for result in sorted_results
            ]


def _is_allowed(current_user: models.User, review_id: int) -> bool:
    is_allowed = current_user.is_admin
    is_allowed = (
        is_allowed
        or db.session.execute(
            sa.select(models.ReviewUserAssoc).filter_by(
                user_id=current_user.id, review_id=review_id
            )
        ).scalar_one_or_none()
        is not None
    )
    return is_allowed


bp.add_url_rule("/<int:id>", view_func=StudyAPI.as_view("study"))
bp.add_url_rule("/", view_func=StudiesAPI.as_view("studies"))
