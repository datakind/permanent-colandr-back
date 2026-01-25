import collections

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from ....lib import constants
from .. import errors


bp = af.APIBlueprint("review_progress", __name__, url_prefix="/reviews/<int:id>")


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
                metadata={
                    "description": "name of review particular step for which to get progress, or 'all' steps"
                },
            ),
            "user_view": af.fields.Boolean(
                load_default=False,
                metadata={
                    "description": (
                        "if True, return progress from the current app user's perspective; "
                        "otherwise, use review-oriented progress numbers"
                    )
                },
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
        # these first two steps are the same, regardless of user_view
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
        if step in ("data_extraction", "all"):
            stmt = (
                sa.select(models.Study.data_extraction_status, sa.func.count())
                .filter_by(review_id=id, fulltext_status="included")
                .group_by(models.Study.data_extraction_status)
            )
            progress = (
                # set default values for all statuses
                {status: 0 for status in constants.EXTRACTION_STATUSES}
                # override actual values for occurring statuses
                | {
                    row.data_extraction_status: row.count
                    for row in db.session.execute(stmt)
                }
            )
            response["data_extraction"] = progress
        if user_view is False:
            # compute all screening status counts using a single query, for perf reasons
            if step == "all":
                # get all screening steps' statuses for review studies
                stmt = sa.select(
                    models.Study.citation_status,
                    models.Study.fulltext_status,
                ).filter_by(review_id=id)
                rows = db.session.execute(stmt).mappings().all()
                # ensure every status is included, i.e. 0 count instead of null/missing
                progress = {
                    "citation_screening": {
                        ss: 0 for ss in constants.SCREENING_STATUSES
                    },
                    "fulltext_screening": {
                        ss: 0 for ss in constants.SCREENING_STATUSES
                    },
                }
                # compute the counts in python rather than sql, for convenience
                progress["citation_screening"] |= dict(
                    collections.Counter(row["citation_status"] for row in rows)
                    # TODO: do we want to filter to dedupe_status == "not_duplicate" ?
                )
                progress["fulltext_screening"] |= dict(
                    collections.Counter(
                        row["fulltext_status"]
                        for row in rows
                        if row["citation_status"] == "included"
                    )
                )
                response |= progress
            elif step == "citation_screening":
                stmt = (
                    sa.select(models.Study.citation_status, sa.func.count())
                    .filter_by(review_id=id)
                    .group_by(models.Study.citation_status)
                )
                progress = (
                    # set default values for all statuses
                    {status: 0 for status in constants.SCREENING_STATUSES}
                    # override actual values for occurring statuses
                    | {
                        row.citation_status: row.count
                        for row in db.session.execute(stmt)
                    }
                )
                response["citation_screening"] = progress
            elif step == "fulltext_screening":
                stmt = (
                    sa.select(models.Study.fulltext_status, sa.func.count())
                    .filter_by(review_id=id, citation_status="included")
                    .group_by(models.Study.fulltext_status)
                )
                progress = (
                    # set default values for all statuses
                    {status: 0 for status in constants.SCREENING_STATUSES}
                    # override actual values for occurring statuses
                    | {
                        row.fulltext_status: row.count
                        for row in db.session.execute(stmt)
                    }
                )
                response["fulltext_screening"] = progress
        else:
            if step in ("citation_screening", "all"):
                user_id = current_user.id
                screenings_cte = (
                    sa.select(
                        models.Screening.study_id,
                        sa.func.array_agg(models.Screening.user_id).label("user_ids"),
                    )
                    .filter_by(review_id=id, stage="citation")
                    .group_by(models.Screening.study_id)
                    .cte("screenings_")
                )
                studies_cte = (
                    sa.select(
                        models.Study.id,
                        models.Study.citation_status,
                        screenings_cte.c.user_ids,
                    )
                    .outerjoin(
                        screenings_cte, models.Study.id == screenings_cte.c.study_id
                    )
                    .where(
                        models.Study.review_id == id,
                        models.Study.dedupe_status == "not_duplicate",
                    )
                    .cte("studies_")
                )
                user_status = sa.case(
                    (
                        studies_cte.c.citation_status.in_(
                            ["included", "excluded", "conflict"]
                        ),
                        studies_cte.c.citation_status,
                    ),
                    (
                        sa.and_(
                            studies_cte.c.citation_status == "screened_once",
                            user_id == sa.any_(studies_cte.c.user_ids),
                        ),
                        "awaiting_coscreener",
                    ),
                    (
                        sa.or_(
                            studies_cte.c.citation_status == "not_screened",
                            user_id != sa.any_(studies_cte.c.user_ids),
                        ),
                        "pending",
                    ),
                ).label("user_status")
                stmt = (
                    sa.select(user_status, sa.func.count().label("count"))
                    .select_from(studies_cte)
                    .group_by(user_status)
                )
                progress = (
                    # set default values for all statuses
                    {status: 0 for status in constants.SCREENING_STATUSES}
                    # override actual values for occurring statuses
                    | {row.user_status: row.count for row in db.session.execute(stmt)}
                )
                response["citation_screening"] = progress
            if step in ("fulltext_screening", "all"):
                user_id = current_user.id
                screenings_cte = (
                    sa.select(
                        models.Screening.study_id,
                        sa.func.array_agg(models.Screening.user_id).label("user_ids"),
                    )
                    .filter_by(review_id=id, stage="fulltext")
                    .group_by(models.Screening.study_id)
                    .cte("screenings_")
                )
                studies_cte = (
                    sa.select(
                        models.Study.id,
                        models.Study.fulltext_status,
                        screenings_cte.c.user_ids,
                    )
                    .outerjoin(
                        screenings_cte, models.Study.id == screenings_cte.c.study_id
                    )
                    .where(
                        models.Study.review_id == id,
                        models.Study.citation_status == "included",
                    )
                    .cte("studies_")
                )
                user_status = sa.case(
                    (
                        studies_cte.c.fulltext_status.in_(
                            ["included", "excluded", "conflict"]
                        ),
                        studies_cte.c.fulltext_status,
                    ),
                    (
                        sa.and_(
                            studies_cte.c.fulltext_status == "screened_once",
                            user_id == sa.any_(studies_cte.c.user_ids),
                        ),
                        "awaiting_coscreener",
                    ),
                    (
                        sa.or_(
                            studies_cte.c.fulltext_status == "not_screened",
                            user_id != sa.any_(studies_cte.c.user_ids),
                        ),
                        "pending",
                    ),
                ).label("user_status")
                stmt = (
                    sa.select(user_status, sa.func.count().label("count"))
                    .select_from(studies_cte)
                    .group_by(user_status)
                )
                progress = (
                    # set default values for all statuses
                    {status: 0 for status in constants.SCREENING_STATUSES}
                    # override actual values for occurring statuses
                    | {row.user_status: row.count for row in db.session.execute(stmt)}
                )
                response["fulltext_screening"] = progress

        current_app.logger.debug("%s got progress for %s", current_user, review)
        return response


bp.add_url_rule("/progress", view_func=ReviewProgressAPI.as_view("review_progress"))
