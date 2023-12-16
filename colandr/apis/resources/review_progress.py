import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_kwargs

from ...extensions import db
from ...lib import constants
from ...models import Review, Study
from ..errors import forbidden_error, not_found_error


ns = Namespace(
    "review_progress",
    path="/reviews/<int:id>",
    description="get review progress counts",
)


@ns.route("/progress")
@ns.doc(
    summary="get review progress on one or all steps",
    produces=["application/json"],
)
class ReviewProgressResource(Resource):
    @ns.doc(
        params={
            "step": {
                "in": "query",
                "type": "string",
                "default": "all",
                "enum": [
                    "planning",
                    "citation_screening",
                    "fulltext_screening",
                    "data_extraction",
                    "all",
                ],
                "description": 'name of review particular step for which to get progress, or "all" steps',
            },
            "user_view": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, return progress from the current app user's perspective; otherwise, use review-oriented progress numbers",
            },
        },
        responses={
            200: "successfully got review progress",
            401: "current app user forbidden to get review progress",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="view_args",
    )
    @use_kwargs(
        {
            "step": ma_fields.Str(
                validate=OneOf(
                    [
                        "planning",
                        "citation_screening",
                        "fulltext_screening",
                        "data_extraction",
                        "all",
                    ]
                ),
                load_default="all",
            ),
            "user_view": ma_fields.Boolean(load_default=False),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, id, step, user_view):
        """get review progress on one or all steps for a single review by id"""
        current_user = jwtext.get_current_user()
        response = {}
        review = db.session.get(Review, id)
        if not review:
            return not_found_error(f"<Review(id={id})> not found")
        if (
            current_user.is_admin is False
            and review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            return forbidden_error(f"{current_user} forbidden to get review progress")
        if step in ("planning", "all"):
            review_plan = review.review_plan
            progress = {
                "objective": bool(review_plan.objective),
                "research_questions": bool(review_plan.research_questions),
                "pico": bool(review_plan.pico),
                "keyterms": bool(review_plan.keyterms),
                "selection_criteria": bool(review_plan.selection_criteria),
                "data_extraction_form": bool(review_plan.data_extraction_form),
            }
            response[
                "planning"
            ] = progress  # {key: val for key, val in progress.items()}
        if step in ("citation_screening", "all"):
            if user_view is False:
                progress = db.session.execute(
                    sa.select(Study.citation_status, db.func.count(1))
                    .filter_by(review_id=id)
                    .group_by(Study.citation_status)
                ).all()
                progress = dict(progress)
                progress = {
                    status: progress.get(status, 0)
                    for status in constants.SCREENING_STATUSES
                }
            else:
                query = """
                    SELECT
                        (CASE
                             WHEN citation_status IN ('included', 'excluded', 'conflict') THEN citation_status
                             WHEN citation_status = 'screened_once' AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                             WHEN citation_status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                         END) AS user_status,
                         COUNT(*)
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
                          WHERE review_id = {review_id}
                          ) AS t
                    WHERE dedupe_status = 'not_duplicate'  -- this is necessary!
                    GROUP BY user_status;
                    """.format(user_id=current_user.id, review_id=id)
                progress = dict(row for row in db.session.execute(sa.text(query)))
                progress = {
                    status: progress.get(status, 0)
                    for status in constants.USER_SCREENING_STATUSES
                }
            response["citation_screening"] = progress
        if step in ("fulltext_screening", "all"):
            if user_view is False:
                progress = db.session.execute(
                    sa.select(Study.fulltext_status, db.func.count(1))
                    .filter_by(review_id=id, citation_status="included")
                    .group_by(Study.fulltext_status)
                ).all()
                progress = dict(progress)
                progress = {
                    status: progress.get(status, 0)
                    for status in constants.SCREENING_STATUSES
                }
            else:
                query = """
                    SELECT
                        (CASE
                             WHEN fulltext_status IN ('included', 'excluded', 'conflict') THEN fulltext_status
                             WHEN fulltext_status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                             WHEN fulltext_status = 'screened_once' AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                         END) AS user_status,
                         COUNT(*)
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
                          WHERE review_id = {review_id}
                          ) AS t
                    WHERE citation_status = 'included'  -- this is necessary!
                    GROUP BY user_status;
                    """.format(user_id=current_user.id, review_id=id)
                progress = dict(row for row in db.session.execute(sa.text(query)))
                progress = {
                    status: progress.get(status, 0)
                    for status in constants.USER_SCREENING_STATUSES
                }
            response["fulltext_screening"] = progress
        if step in ("data_extraction", "all"):
            progress = db.session.execute(
                sa.select(Study.data_extraction_status, db.func.count(1))
                .filter_by(review_id=id, fulltext_status="included")
                .group_by(Study.data_extraction_status)
            ).all()
            progress = dict(progress)
            progress = {
                status: progress.get(status, 0)
                for status in constants.EXTRACTION_STATUSES
            }
            response["data_extraction"] = progress

        current_app.logger.debug("got progress for %s", review)

        return response
