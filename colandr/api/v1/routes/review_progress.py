import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from ....lib import constants
from .. import errors


bp = af.APIBlueprint("review progress", __name__, url_prefix="/reviews/<int:id>")


class ReviewProgressAPI(MethodView):
    @bp.doc(
        summary="get review progress on step(s)",
        responses={
            200: "successfully got review progress",
            401: "current app user forbidden to get review progress",
            404: "no review matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "step": af.fields.String(
                validate=af.validators.OneOf(
                    [
                        "planning",
                        "citation_screening",
                        "fulltext_screening",
                        "data_extraction",
                        "all",
                    ]
                ),
                load_default="all",
                description="name of review particular step for which to get progress, or 'all' steps",
            ),
            "user_view": af.fields.Boolean(
                load_default=False,
                description=(
                    "if True, return progress from the current app user's perspective; "
                    "otherwise, use review-oriented progress numbers"
                ),
            ),
        },
        location="query",
    )
    @bp.output(
        {
            "planning": af.fields.Dict(
                keys=af.fields.String(), values=af.fields.Boolean(), required=False
            ),
            "citation_screening": af.fields.Dict(
                keys=af.fields.String(), values=af.fields.Integer(), required=False
            ),
            "fulltext_screening": af.fields.Dict(
                keys=af.fields.String(), values=af.fields.Integer(), required=False
            ),
            "data_extraction": af.fields.Dict(
                keys=af.fields.String(), values=af.fields.Integer(), required=False
            ),
        }
    )
    @jwtext.jwt_required()
    def get(self, id, query_data):
        step = query_data["step"]
        user_view = query_data["user_view"]
        current_user = jwtext.get_current_user()
        review = db.session.get(models.Review, id)

        if not review:
            raise errors.NotFoundError(message=f"<Review(id={id})> not found")

        if (
            current_user.is_admin is False
            and review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get review progress"
            )

        response = {}
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
            response["planning"] = progress
        if step in ("citation_screening", "all"):
            if user_view is False:
                progress = {status: 0 for status in constants.SCREENING_STATUSES}
                progress_stmt = (
                    sa.select(models.Study.citation_status, sa.func.count())
                    .filter_by(review_id=id)
                    .group_by(models.Study.citation_status)
                )
                progress |= {
                    row.citation_status: row.count
                    for row in db.session.execute(progress_stmt)
                }
            else:
                # TODO: figure out how to ORM-ify this
                query = """
                    SELECT
                        (CASE
                             WHEN citation_status IN ('included', 'excluded', 'conflict') THEN citation_status
                             WHEN citation_status = 'screened_once' AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                             WHEN citation_status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                         END) AS user_status,
                         COUNT(*)
                    FROM (
                        SELECT
                            studies.id,
                            studies.dedupe_status,
                            studies.citation_status,
                            screenings_.user_ids
                        FROM studies
                        LEFT JOIN (
                            SELECT
                                study_id,
                                ARRAY_AGG(user_id) AS user_ids
                            FROM screenings
                            WHERE stage = 'citation'
                            GROUP BY study_id
                        ) AS screenings_ ON studies.id = screenings_.study_id
                        WHERE review_id = {review_id}
                    ) AS t
                    WHERE dedupe_status = 'not_duplicate'  -- this is necessary!
                    GROUP BY user_status;
                    """.format(user_id=current_user.id, review_id=id)
                progress = {
                    row.user_status: row.count
                    for row in db.session.execute(sa.text(query))
                }
                progress = {
                    status: progress.get(status, 0)
                    for status in constants.USER_SCREENING_STATUSES
                }
            response["citation_screening"] = progress
        if step in ("fulltext_screening", "all"):
            if user_view is False:
                progress = {status: 0 for status in constants.SCREENING_STATUSES}
                progress_stmt = (
                    sa.select(models.Study.fulltext_status, sa.func.count())
                    .filter_by(review_id=id, citation_status="included")
                    .group_by(models.Study.fulltext_status)
                )
                progress |= {
                    row.fulltext_status: row.count
                    for row in db.session.execute(progress_stmt)
                }
            else:
                # TODO: figure out how to ORM-ify this
                query = """
                    SELECT
                        (CASE
                             WHEN fulltext_status IN ('included', 'excluded', 'conflict') THEN fulltext_status
                             WHEN fulltext_status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                             WHEN fulltext_status = 'screened_once' AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                         END) AS user_status,
                         COUNT(*)
                    FROM (
                        SELECT
                            studies.id,
                            studies.citation_status,
                            studies.fulltext_status,
                            screenings_.user_ids
                        FROM studies
                        LEFT JOIN (
                            SELECT
                                study_id,
                                ARRAY_AGG(user_id) AS user_ids
                            FROM screenings
                            WHERE stage = 'fulltext'
                            GROUP BY study_id
                        ) AS screenings_ ON studies.id = screenings_.study_id
                        WHERE review_id = {review_id}
                    ) AS t
                    WHERE citation_status = 'included'  -- this is necessary!
                    GROUP BY user_status;
                    """.format(user_id=current_user.id, review_id=id)
                progress = {
                    row.user_status: row.count
                    for row in db.session.execute(sa.text(query))
                }
                progress = {
                    status: progress.get(status, 0)
                    for status in constants.USER_SCREENING_STATUSES
                }
            response["fulltext_screening"] = progress
        if step in ("data_extraction", "all"):
            progress = {status: 0 for status in constants.EXTRACTION_STATUSES}
            progress_stmt = (
                sa.select(models.Study.data_extraction_status, sa.func.count())
                .filter_by(review_id=id, fulltext_status="included")
                .group_by(models.Study.data_extraction_status)
            )
            progress |= {
                row.data_extraction_status: row.count
                for row in db.session.execute(progress_stmt)
            }
            response["data_extraction"] = progress

        current_app.logger.debug("%s got progress for %s", current_user, review)
        return response


bp.add_url_rule("/progress", view_func=ReviewProgressAPI.as_view("review_progress"))
