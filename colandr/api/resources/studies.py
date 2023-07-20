import os
import random
from operator import itemgetter

import flask_praetorian
import joblib
import numpy as np
from flask import current_app, g
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Length, OneOf, Range
from sqlalchemy import asc, desc, text
from sqlalchemy.sql import operators
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants
from ...lib.constants import (
    CITATION_RANKING_MODEL_FNAME,
    DEDUPE_STATUSES,
    EXTRACTION_STATUSES,
    USER_SCREENING_STATUSES,
)
from ...lib.nlp import reviewer_terms
from ...models import Citation, Review, Study, db
from ..errors import forbidden_error, not_found_error
from ..schemas import StudySchema
from ..swagger import study_model

ns = Namespace("studies", path="/studies", description="get, delete, update studies")


@ns.route("/<int:id>")
@ns.doc(
    summary="get, delete, and modify data for single studies",
    produces=["application/json"],
)
class StudyResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of review fields to return",
            },
        },
        responses={
            200: "successfully got study record",
            403: "current app user forbidden to get study record",
            404: "no study with matching id was found",
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
    def get(self, id, fields):
        """get record for a single study by id"""
        current_user = flask_praetorian.current_user()
        study = db.session.query(Study).get(id)
        if not study:
            return not_found_error("<Study(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and study.review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(
                "{} forbidden to get this study".format(current_user)
            )
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", study)
        return StudySchema(only=fields).dump(study)

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        responses={
            200: "request was valid, but record not deleted because `test=False`",
            204: "successfully deleted study record",
            403: "current app user forbidden to delete study record",
            404: "no study with matching id was found",
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
    @use_kwargs({"test": ma_fields.Boolean(load_default=False)}, location="query")
    def delete(self, id, test):
        """delete record for a single study by id"""
        current_user = flask_praetorian.current_user()
        study = db.session.query(Study).get(id)
        if not study:
            return not_found_error("<Study(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and study.review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(
                "{} forbidden to delete this study".format(current_user)
            )
        db.session.delete(study)
        if test is False:
            db.session.commit()
            current_app.logger.info("deleted %s", study)
            return "", 204
        else:
            db.session.rollback()
            return "", 200

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        body=(study_model, "study data to be modified"),
        responses={
            200: "study data was modified (if test = False)",
            403: "current app user forbidden to modify study; specified field may not be modified",
            404: "no study with matching id was found",
        },
    )
    @use_args(StudySchema(only=["data_extraction_status", "tags"]), location="json")
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @use_kwargs({"test": ma_fields.Boolean(load_default=False)}, location="query")
    def put(self, args, id, test):
        """modify record for a single study by id"""
        current_user = flask_praetorian.current_user()
        study = db.session.query(Study).get(id)
        if not study:
            return not_found_error("<Study(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and study.review.users.filter_by(id=current_user.id).one_or_none() is None
        ):
            return forbidden_error(
                "{} forbidden to modify this study".format(current_user)
            )
        for key, value in args.items():
            if key == "data_extraction_status":
                if study.fulltext_status != "included":
                    return forbidden_error(
                        "<Study(id={})> data_extraction_status can't be set until fulltext has passed screening".format(
                            id
                        )
                    )
            setattr(study, key, value)
        if test is False:
            db.session.commit()
            current_app.logger.info("modified %s", study)
        else:
            db.session.rollback()
        return StudySchema().dump(study)


@ns.route("")
@ns.doc(
    summary="get collections of matching studies",
    produces=["application/json"],
)
class StudiesResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier for review whose studies are to be fetched",
            },
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of study fields to return",
            },
            "dedupe_status": {
                "in": "query",
                "type": "string",
                "enum": DEDUPE_STATUSES,
                "description": "filter studies to only those with matching deduplication statuses",
            },
            "citation_status": {
                "in": "query",
                "type": "string",
                "enum": USER_SCREENING_STATUSES,
                "description": "filter studies to only those with matching citation statuses",
            },
            "fulltext_status": {
                "in": "query",
                "type": "string",
                "enum": USER_SCREENING_STATUSES,
                "description": "filter studies to only those with matching fulltext statuses",
            },
            "data_extraction_status": {
                "in": "query",
                "type": "string",
                "enum": EXTRACTION_STATUSES,
                "description": "filter studies to only those with matching data extraction statuses",
            },
            "tag": {
                "in": "query",
                "type": "string",
                "description": "filter studies to only those with a matching (user-assigned) tag",
            },
            "tsquery": {
                "in": "query",
                "type": "string",
                "description": "filter studies to only those whose text content contains this word or phrase",
            },
            "order_by": {
                "in": "query",
                "type": "string",
                "enum": ["recency", "relevance"],
                "description": "order matching studies by either date imported or expected relevance",
            },
            "order_dir": {
                "in": "query",
                "type": "string",
                "enum": ["ASC", "DESC"],
                "description": "direction of ordering, either in ascending or descending order",
            },
            "page": {
                "in": "query",
                "type": "integer",
                "description": "page number of the collection of ordered, matching studies, starting at 0",
            },
            "per_page": {
                "in": "query",
                "type": "integer",
                "description": "number of studies to include per page",
            },
        },
        responses={
            200: "successfully got matching study record(s)",
            403: "current app user forbidden to get studies for this review",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "fields": DelimitedList(
                ma_fields.String(), delimiter=",", load_default=None
            ),
            "dedupe_status": ma_fields.String(
                load_default=None, validate=OneOf(DEDUPE_STATUSES)
            ),
            "citation_status": ma_fields.String(
                load_default=None, validate=OneOf(USER_SCREENING_STATUSES)
            ),
            "fulltext_status": ma_fields.String(
                load_default=None, validate=OneOf(USER_SCREENING_STATUSES)
            ),
            "data_extraction_status": ma_fields.String(
                load_default=None, validate=OneOf(EXTRACTION_STATUSES)
            ),
            "tag": ma_fields.String(load_default=None, validate=Length(max=25)),
            "tsquery": ma_fields.String(load_default=None, validate=Length(max=50)),
            "order_by": ma_fields.String(
                load_default="recency", validate=OneOf(["recency", "relevance"])
            ),
            "order_dir": ma_fields.String(
                load_default="DESC", validate=OneOf(["ASC", "DESC"])
            ),
            "page": ma_fields.Int(load_default=0, validate=Range(min=0)),
            "per_page": ma_fields.Int(
                load_default=25, validate=OneOf([10, 25, 50, 100, 5000])
            ),
        },
        location="query",
    )
    def get(
        self,
        review_id,
        fields,
        dedupe_status,
        citation_status,
        fulltext_status,
        data_extraction_status,
        tag,
        tsquery,
        order_by,
        order_dir,
        page,
        per_page,
    ):
        """get study record(s) for one or more matching studies"""
        current_user = flask_praetorian.current_user()
        review = db.session.query(Review).get(review_id)
        if not review:
            return not_found_error("<Review(id={})> not found".format(review_id))
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=review_id).one_or_none() is None
        ):
            return forbidden_error(
                "{} forbidden to get studies from this review".format(current_user)
            )
        if fields and "id" not in fields:
            fields.append("id")
        # build the query by components
        query = review.studies

        if dedupe_status is not None:
            query = query.filter(Study.dedupe_status == dedupe_status)

        if citation_status is not None:
            if citation_status in {"conflict", "excluded", "included"}:
                query = query.filter(Study.citation_status == citation_status)
            elif citation_status == "pending":
                stmt = """
                    SELECT t.id
                    FROM (SELECT
                              studies.id,
                              studies.dedupe_status,
                              studies.citation_status,
                              screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT citation_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM citation_screenings
                                     GROUP BY citation_id
                                     ) AS screenings
                          ON studies.id = screenings.citation_id
                          ) AS t
                    WHERE
                        t.dedupe_status = 'not_duplicate' -- this is necessary!
                        AND t.citation_status NOT IN ('excluded', 'included', 'conflict')
                        AND (t.citation_status = 'not_screened' OR NOT {user_id} = ANY(t.user_ids))
                    """.format(
                    user_id=current_user.id
                )
                query = query.filter(Study.id.in_(text(stmt)))
            elif citation_status == "awaiting_coscreener":
                stmt = """
                    SELECT t.id
                    FROM (SELECT studies.id, studies.citation_status, screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT citation_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM citation_screenings
                                     GROUP BY citation_id
                                     ) AS screenings
                          ON studies.id = screenings.citation_id
                          ) AS t
                    WHERE
                        t.citation_status = 'screened_once'
                        AND {user_id} = ANY(t.user_ids)
                    """.format(
                    user_id=current_user.id
                )
                query = query.filter(Study.id.in_(text(stmt)))

        if fulltext_status is not None:
            if fulltext_status in {"conflict", "excluded", "included"}:
                query = query.filter(Study.fulltext_status == fulltext_status)
            elif fulltext_status == "pending":
                stmt = """
                    SELECT t.id
                    FROM (SELECT
                              studies.id,
                              studies.citation_status,
                              studies.fulltext_status,
                              screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON studies.id = screenings.fulltext_id
                          ) AS t
                    WHERE
                        t.citation_status = 'included' -- this is necessary!
                        AND t.fulltext_status NOT IN ('excluded', 'included', 'conflict')
                        AND (t.fulltext_status = 'not_screened' OR NOT {user_id} = ANY(t.user_ids))
                    """.format(
                    user_id=current_user.id
                )
                query = query.filter(Study.id.in_(text(stmt)))
            elif fulltext_status == "awaiting_coscreener":
                stmt = """
                    SELECT t.id
                    FROM (SELECT studies.id, studies.fulltext_status, screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON studies.id = screenings.fulltext_id
                          ) AS t
                    WHERE
                        t.fulltext_status = 'screened_once'
                        AND {user_id} = ANY(t.user_ids)
                    """.format(
                    user_id=current_user.id
                )
                query = query.filter(Study.id.in_(text(stmt)))

        if data_extraction_status is not None:
            if data_extraction_status == "not_started":
                query = query.filter(
                    Study.data_extraction_status == data_extraction_status
                ).filter(
                    Study.fulltext_status == "included"
                )  # this is necessary!
            else:
                query = query.filter(
                    Study.data_extraction_status == data_extraction_status
                )

        if tag:
            query = query.filter(Study.tags.any(tag, operator=operators.eq))

        if tsquery:
            if order_by != "relevance":  # HACK...
                query = query.join(Citation, Citation.id == Study.id).filter(
                    Citation.text_content.match(tsquery)
                )

        # order, offset, and limit
        if order_by == "recency":
            order_by = desc(Study.id) if order_dir == "DESC" else asc(Study.id)
            query = query.order_by(order_by)
            query = query.offset(page * per_page).limit(per_page)
            return StudySchema(many=True, only=fields).dump(query.all())

        elif order_by == "relevance":
            query = query.join(Citation, Citation.id == Study.id)
            if tsquery:
                query = query.filter(Citation.text_content.match(tsquery))

            # get results and corresponding relevance scores
            results = query.order_by(db.func.random()).limit(1000).all()
            scores = None

            # best option: we have a trained citation ranking model
            fname = CITATION_RANKING_MODEL_FNAME.format(review_id=review_id)
            filepath = os.path.join(
                current_app.config["RANKING_MODELS_DIR"], str(review_id), fname
            )
            if os.path.isfile(filepath):
                clf = joblib.load(filepath)
                X = np.vstack(
                    tuple(
                        result.citation.text_content_vector_rep
                        for result in results
                        if result.citation.text_content_vector_rep
                    )
                )
                scores = clf.decision_function(X).tolist()

            # next best option: both positive and negative keyterms
            if not scores:
                review_plan = review.review_plan
                suggested_keyterms = review_plan.suggested_keyterms
                if suggested_keyterms:
                    incl_regex, excl_regex = reviewer_terms.get_incl_excl_terms_regex(
                        review_plan.suggested_keyterms
                    )
                    scores = [
                        reviewer_terms.get_incl_excl_terms_score(
                            incl_regex, excl_regex, result.citation.text_content
                        )
                        for result in results
                    ]

            # last option: just reviewer terms
            if not scores:
                keyterms = review_plan.keyterms
                if keyterms:
                    keyterms_regex = reviewer_terms.get_keyterms_regex(keyterms)
                    scores = [
                        reviewer_terms.get_keyterms_score(
                            keyterms_regex, result.citation.text_content
                        )
                        for result in results
                    ]

            # well fuck, we're out of options! let's order results randomly...
            if not scores:
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
            return StudySchema(many=True, only=fields).dump(
                sorted_results[offset : offset + per_page]
            )
