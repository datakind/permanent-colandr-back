import random

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from sqlalchemy.dialects import postgresql as pg

from .... import models, tasks
from ....extensions import db
from ....utils import assign_status
from .. import errors, schemas
from . import auth


bp = af.APIBlueprint("admin", __name__, url_prefix="/admin")


@bp.post("/users")
@bp.doc(
    summary="create new user",
    responses={
        200: "user was created",
        403: "current app user forbidden to create user",
    },
    security="TokenAuth",
)
@bp.input(schemas.UserSchema, location="json")
@bp.output(schemas.UserSchema)
@auth.jwt_admin_required()
def post_users(json_data):
    current_user = jwtext.get_current_user()
    user = models.User(**json_data)
    if not user.is_confirmed:
        user.is_confirmed = True
        current_app.logger.warning("[ADMIN] setting %s is_confirmed to True", user)
    db.session.add(user)
    db.session.commit()
    current_app.logger.info("[ADMIN] %s created %s", current_user, user)
    return user


@bp.get("/reviews")
@bp.doc(
    summary="get one or multiple reviews",
    security="TokenAuth",
)
@bp.input(
    {
        "review_ids": af.fields.DelimitedList(
            af.fields.String(),
            required=False,
            delimiter=",",
            description="comma-delimited list-as-string of review ids to return",
        ),
        "user_id": af.fields.Integer(
            required=False,
            delimiter=",",
            description="id of user who's a member of the reviews to be returned",
        ),
    },
    location="query",
)
@bp.output(schemas.ReviewV2Schema(many=True))
@auth.jwt_admin_required()
def get_reviews(query_data):
    review_ids = (
        [int(review_id) for review_id in query_data["review_ids"]]
        if query_data.get("review_ids")
        else None
    )
    user_id = query_data.get("user_id")
    if not bool(review_ids) ^ bool(user_id):
        raise errors.BadRequestError(
            message="either 'review_ids' or 'user_id' must be specified"
        )

    current_user = jwtext.get_current_user()

    if review_ids is not None:
        reviews = (
            db.session.execute(
                sa.select(models.Review).filter(
                    models.Review.id == sa.any_(pg.array(review_ids))
                )
            )
            .scalars()
            .all()
        )
    else:
        user = db.session.get(models.User, user_id)
        if user:
            reviews = user.reviews
            review_ids = [review.id for review in reviews]
        else:
            raise errors.NotFoundError(message=f"<User(id={user_id})> not found")

    current_app.logger.info(
        "[ADMIN] %s got records for reviews %s", current_user, review_ids
    )
    return reviews


@bp.post("/citations/screenings")
@bp.doc(
    summary="create one or multiple citation screenings",
    responses={
        200: "successfully created citation screening record(s)",
        403: "current app user forbidden to create citation screening records",
        404: "no review with matching id was found",
    },
    security="TokenAuth",
)
@bp.input(
    schemas.ScreeningSchema(many=True, partial=["user_id", "review_id"]),
    location="json",
)
@bp.input(
    {
        "review_id": af.fields.Integer(
            required=True,
            validate=af.validators.Range(min=1),
            description="unique identifier of review for which to create citation screenings",
        ),
        "user_id": af.fields.Integer(
            validate=af.validators.Range(min=1),
            description="unique identifier of user screening citations, if not current app user",
        ),
    },
    location="query",
)
@bp.output({}, 200)
@auth.jwt_admin_required()
def post_citation_screenings(json_data, query_data):
    review_id = query_data["review_id"]
    user_id = query_data.get("user_id")
    current_user = jwtext.get_current_user()
    review = db.session.get(models.Review, review_id)

    if not review:
        raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

    # bulk insert screenings
    screenings_attrs = {
        "user_id": user_id or current_user.id,
        "review_id": review_id,
        "stage": "citation",
    }
    screenings_to_insert = [screening | screenings_attrs for screening in json_data]
    for screening in screenings_to_insert:
        if "citation_id" in screening:
            screening["study_id"] = screening.pop("citation_id")
    db.session.execute(sa.insert(models.Screening), screenings_to_insert)
    db.session.commit()
    current_app.logger.info(
        "[ADMIN] %s inserted %s citation screenings",
        current_user,
        len(screenings_to_insert),
    )

    # bulk update statuses
    study_ids: list[int] = sorted(s["study_id"] for s in screenings_to_insert)
    study_num_citation_reviewers: list[int] = random.choices(
        [num_pct["num"] for num_pct in review.citation_reviewer_num_pcts],
        weights=[num_pct["pct"] for num_pct in review.citation_reviewer_num_pcts],
        k=len(study_ids),
    )
    results = db.session.execute(
        sa.select(models.Screening.study_id, sa.func.array_agg(models.Screening.status))
        .where(models.Screening.stage == "citation")
        .where(models.Screening.study_id == sa.any_(pg.array(study_ids)))
        .group_by(models.Screening.study_id)
        .order_by(models.Screening.study_id)
    )
    studies_to_update = [
        {"id": row[0], "citation_status": assign_status(row[1], num_reviewers)}
        for row, num_reviewers in zip(results, study_num_citation_reviewers)
    ]
    db.session.execute(sa.update(models.Study), studies_to_update)
    db.session.commit()
    current_app.logger.info(
        "[ADMIN] %s updated citation_status for %s studies",
        current_user,
        len(studies_to_update),
    )

    # get include/exclude counts on review
    status_counts = review.num_citations_by_status(["included", "excluded"])
    n_included = status_counts.get("included", 0)
    n_excluded = status_counts.get("excluded", 0)
    # do we have to suggest keyterms?
    if n_included >= 25 and n_excluded >= 25:
        sample_size = min(n_included, n_excluded)
        tasks.suggest_keyterms.apply_async(args=[review_id, sample_size])


@bp.post("/fulltexts/screenings")
@bp.doc(
    summary="create one or multiple fulltext screenings",
    responses={
        200: "successfully created fulltext screening record(s)",
        403: "current app user forbidden to create fulltext screening records",
        404: "no review with matching id was found",
    },
    security="TokenAuth",
)
@bp.input(
    schemas.ScreeningSchema(many=True, partial=["user_id", "review_id"]),
    location="json",
)
@bp.input(
    {
        "review_id": af.fields.Integer(
            required=True,
            validate=af.validators.Range(min=1),
            description="unique identifier of review for which to create fulltext screenings",
        ),
        "user_id": af.fields.Integer(
            load_default=None,
            validate=af.validators.Range(min=1),
            description="unique identifier of user screening fulltexts, if not current app user",
        ),
    },
    location="query",
)
@bp.output({}, 200)
@auth.jwt_admin_required()
def post_fulltext_screenings(json_data, query_data):
    review_id = query_data["review_id"]
    user_id = query_data.get("user_id")
    current_user = jwtext.get_current_user()
    review = db.session.get(models.Review, review_id)

    if not review:
        raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

    # bulk insert screenings
    screenings_attrs = {
        "user_id": user_id or current_user.id,
        "review_id": review_id,
        "stage": "fulltext",
    }
    screenings_to_insert = [screening | screenings_attrs for screening in json_data]
    for screening in screenings_to_insert:
        if "fulltext_id" in screening:
            screening["study_id"] = screening.pop("fulltext_id")
    db.session.execute(sa.insert(models.Screening), screenings_to_insert)
    db.session.commit()
    current_app.logger.info(
        "[ADMIN] %s inserted %s fulltext screenings",
        current_user,
        len(screenings_to_insert),
    )

    # bulk update statuses
    study_ids: list[int] = sorted(s["study_id"] for s in screenings_to_insert)
    study_num_fulltext_reviewers: list[int] = random.choices(
        [num_pct["num"] for num_pct in review.fulltext_reviewer_num_pcts],
        weights=[num_pct["pct"] for num_pct in review.fulltext_reviewer_num_pcts],
        k=len(study_ids),
    )
    results = db.session.execute(
        sa.select(models.Screening.study_id, sa.func.array_agg(models.Screening.status))
        .where(models.Screening.stage == "fulltext")
        .where(models.Screening.study_id == sa.any_(pg.array(study_ids)))
        .group_by(models.Screening.study_id)
        .order_by(models.Screening.study_id)
    )
    studies_to_update = [
        {"id": row[0], "fulltext_status": assign_status(row[1], num_reviewers)}
        for row, num_reviewers in zip(results, study_num_fulltext_reviewers)
    ]
    db.session.execute(sa.update(models.Study), studies_to_update)
    db.session.commit()
    current_app.logger.info(
        "[ADMIN] %s updated citation_status for %s studies",
        current_user,
        len(studies_to_update),
    )

    # now add data extractions for included fulltexts
    # normally this is done automatically, but not when we're hacking
    # and doing bulk changes to the database
    results = db.session.execute(
        sa.select(models.Study.id)
        .filter_by(review_id=review_id, fulltext_status="included")
        .filter(~models.Study.data_extraction.has())
        .order_by(models.Study.id)
    ).scalars()
    data_extractions_to_insert = [
        {"id": result, "review_id": review_id} for result in results
    ]
    db.session.execute(sa.insert(models.DataExtraction), data_extractions_to_insert)
    db.session.commit()
    current_app.logger.info(
        "[ADMIN] %s inserted %s data extractions",
        current_user,
        len(data_extractions_to_insert),
    )
    # get include/exclude counts on review
    # status_counts = review.num_fulltexts_by_status(["included", "excluded"])
    # n_included = status_counts.get("included", 0)
    # n_excluded = status_counts.get("excluded", 0)
    # TODO: do stuff given num included/excluded?
