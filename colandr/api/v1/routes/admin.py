import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from sqlalchemy.dialects import postgresql as pg

from .... import models
from ....extensions import db
from .. import errors, schemas
from . import auth


bp = af.APIBlueprint("admin", __name__, url_prefix="/admin")


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

    current_app.logger.info("%s got records for reviews %s", current_user, review_ids)
    return reviews
