import datetime
import typing as t

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models, tasks
from ....extensions import db
from ....utils import assign_status
from .. import errors, schemas


bp = af.APIBlueprint("fulltext_screenings", __name__, url_prefix="/fulltexts")


class FulltextScreeningAPI(MethodView):
    @bp.doc(
        summary="get screenings for a single fulltext",
        responses={
            200: "successfully got fulltext screening(s)",
            403: "current app user forbidden to get fulltext screening(s)",
            404: "no fulltext matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.FieldsSchema, location="query")
    @bp.output(schemas.ScreeningSchema(many=True))
    @jwtext.jwt_required()
    def get(self, id, query_data):
        fields = query_data.get("fields_")
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if (
            current_user.is_admin is False
            and db.session.execute(
                current_user.review_user_assoc.select().filter_by(
                    review_id=study.review_id
                )
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get fulltext screenings for this review"
            )

        screenings = db.session.execute(
            study.screenings.select().filter_by(stage="fulltext")
        ).scalars()
        if not screenings:
            raise errors.NotFoundError(
                message=f"no screenings for <Study(id={id})> found"
            )

        # HACK: hide the consolidated (v2) screening schema from this api
        if fields and "fulltext_id" in fields:
            fields.append("study_id")
            fields.remove("fulltext_id")
        results = [
            _convert_screening_v2_into_v1(screening, fields) for screening in screenings
        ]
        current_app.logger.debug(
            "%s got %s screenings for %s", current_user, len(results), study
        )
        return results

    @bp.doc(
        summary="create a screening for a single fulltext",
        responses={
            200: "fulltext screening was created",
            403: "current app user forbidden to create fulltext screening; has already created a screening for this fulltext, or no screening can be created because the full-text has not yet been uploaded",
            404: "no fulltext matching id was found",
            422: "invalid fulltext screening record",
        },
        security="TokenAuth",
    )
    @bp.input(
        schemas.ScreeningSchema(partial=["user_id", "review_id"]), location="json"
    )
    @bp.output(schemas.ScreeningSchema)
    @jwtext.jwt_required()
    def post(self, id, json_data):
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Fulltext(id={id})> not found")

        if (
            current_user.is_admin is False
            and db.session.execute(
                current_user.review_user_assoc.select().filter_by(
                    review_id=study.review_id
                )
            ).one_or_none()
            is None
        ) or study.review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to screen fulltexts for this review"
            )

        if not study.fulltext:
            raise errors.ForbiddenError(
                message=f"user can't screen {study} fulltext without it being uploaded"
            )

        # validate and add screening
        if json_data["status"] == "excluded" and not json_data["exclude_reasons"]:
            raise errors.BadRequestError(
                message="screenings that exclude must provide a reason"
            )

        if current_user.is_admin:
            if "user_id" not in json_data:
                raise errors.BadRequestError(
                    message="admins must specify 'user_id' when creating a fulltext screening"
                )
            else:
                user_id = json_data["user_id"]
        else:
            user_id = current_user.id

        if db.session.execute(
            study.screenings.select().filter_by(
                stage="fulltext", user_id=current_user.id
            )
        ).one_or_none():
            raise errors.ForbiddenError(
                message=f"{current_user} has already screened {study}"
            )

        screening = models.Screening(
            user_id=user_id,
            review_id=study.review_id,
            study_id=id,
            stage="fulltext",
            status=json_data["status"],
            exclude_reasons=json_data["exclude_reasons"],
        )  # type: ignore
        study.screenings.add(screening)
        db.session.commit()

        current_app.logger.info("%s created %s", current_user, screening)
        tasks.train_study_ranker_model.apply_async(args=[study.review_id, screening.id])
        return _convert_screening_v2_into_v1(screening)

    @bp.doc(
        summary="modify a screening for a single fulltext",
        responses={
            200: "fulltext screening data was modified",
            403: "current app user forbidden to modify fulltext screening",
            404: "no fulltext matching id was found, or no fulltext screening exists for current app user",
            422: "invalid modified fulltext screening data",
        },
        security="TokenAuth",
    )
    @bp.input(
        schemas.ScreeningSchema(
            only=["user_id", "status", "exclude_reasons"],
            partial=["exclude_reasons"],
        ),
        location="json",
    )
    @bp.output(schemas.ScreeningSchema)
    @jwtext.jwt_required()
    def put(self, id, json_data):
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if current_user.is_admin is True and "user_id" in json_data:
            screening = db.session.execute(
                study.screenings.select().filter_by(
                    stage="fulltext", user_id=json_data["user_id"]
                )
            ).scalar_one_or_none()
        else:
            screening = db.session.execute(
                study.screenings.select().filter_by(
                    stage="fulltext", user_id=current_user.id
                )
            ).scalar_one_or_none()
        if not screening:
            raise errors.NotFoundError(
                message=f"{current_user} has not screened this fulltext"
            )

        if json_data["status"] == "excluded" and not json_data["exclude_reasons"]:
            raise errors.BadRequestError(
                message="screenings that exclude must provide a reason"
            )

        for key, value in json_data.items():
            setattr(screening, key, value)
        db.session.commit()

        current_app.logger.info("%s modified %s", current_user, screening)
        return _convert_screening_v2_into_v1(screening)

    @bp.doc(
        summary="delete current app user's screening for a single fulltext",
        responses={
            204: "successfully deleted fulltext screening",
            403: "current app user forbidden to delete fulltext screening; has not screened fulltext, so nothing to delete",
            404: "no fulltext matching id was found",
        },
    )
    @bp.output({}, 204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if (
            db.session.execute(
                current_user.review_user_assoc.select().filter_by(
                    review_id=study.review_id
                )
            ).one_or_none()
            is None
        ) or study.review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete fulltext screening for this review"
            )

        screening = db.session.execute(
            study.screenings.select().filter_by(
                stage="fulltext", user_id=current_user.id
            )
        ).scalar_one_or_none()
        if not screening:
            raise errors.ForbiddenError(
                message=f"{current_user} has not screened {study}, so nothing to delete"
            )

        db.session.delete(screening)
        db.session.commit()
        current_app.logger.info("%s deleted %s", current_user, screening)
        return ""


class FulltextScreeningsAPI(MethodView):
    @bp.doc(
        summary="get all fulltext screenings by citation, user, or review id",
        responses={
            200: "successfully got fulltext screening record(s)",
            400: "bad request: fulltext_id, user_id, or review_id required",
            403: "current app user forbidden to get fulltext screening record(s)",
            404: "no fulltext with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "fulltext_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of fulltext for which to get all fulltext screenings"
                },
            ),
            "user_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of user for which to get all fulltext screenings"
                },
            ),
            "review_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of review for which to get fulltext screenings"
                },
            ),
            "status_counts": af.fields.Boolean(
                load_default=False,
                metadata={
                    "description": (
                        "if True, group screenings by status and return the counts; "
                        "if False, return the screening records themselves"
                    )
                },
            ),
        },
        location="query",
    )
    # TODO: add @bp.output(schemas.ScreeningSchema)
    # and move the status-counts variation to a separate endpoint
    # because we can't do both with one schema -- nor should we
    @jwtext.jwt_required()
    def get(self, query_data):
        fulltext_id = query_data.get("fulltext_id")
        user_id = query_data.get("user_id")
        review_id = query_data.get("review_id")
        status_counts = query_data.get("status_counts")
        current_user = jwtext.get_current_user()

        if not any([fulltext_id, user_id, review_id]):
            raise errors.BadRequestError(
                message="fulltext, user, and/or review id must be specified"
            )

        stmt = (
            sa.select(models.Screening)
            if status_counts is False
            else sa.select(models.Screening.status, db.func.count(1))
        )
        stmt = stmt.where(models.Screening.stage == "fulltext")
        if fulltext_id is not None:
            # check user authorization
            study = db.session.get(models.Study, fulltext_id)
            if not study:
                raise errors.NotFoundError(
                    message=f"<Study(id={fulltext_id})> not found"
                )
            if (
                current_user.is_admin is False
                and study.review.review_user_assoc.filter_by(
                    user_id=current_user.id
                ).one_or_none()
                is None
            ):
                raise errors.ForbiddenError(
                    message=f"{current_user} forbidden to get screenings for {study}"
                )
            stmt = stmt.where(models.Screening.study_id == fulltext_id)
        if user_id is not None:
            # check user authorization
            user = db.session.get(models.User, user_id)
            if not user:
                raise errors.NotFoundError(message=f"<User(id={user_id})> not found")
            if current_user.is_admin is False and not any(
                user_id == user.id
                for review in current_user.reviews
                for user in review.users
            ):
                raise errors.ForbiddenError(
                    message=f"{current_user} forbidden to get screenings for {user}"
                )
            stmt = stmt.where(models.Screening.user_id == user_id)
        if review_id is not None:
            # check user authorization
            review = db.session.get(models.Review, review_id)
            if not review:
                raise errors.NotFoundError(
                    message=f"<Review(id={review_id})> not found"
                )
            if (
                current_user.is_admin is False
                and review.review_user_assoc.filter_by(
                    user_id=current_user.id
                ).one_or_none()
                is None
            ):
                raise errors.ForbiddenError(
                    message=f"{current_user} forbidden to get screenings for {review}"
                )
            stmt = stmt.where(models.Screening.review_id == review_id)

        if status_counts is True:
            stmt = stmt.group_by(models.Screening.status)
            return {row.status: row.count for row in db.session.execute(stmt)}
        else:
            results = db.session.execute(stmt).scalars()
            return [_convert_screening_v2_into_v1(record) for record in results]


def _convert_screening_v2_into_v1(
    screening: models.Screening, fields: t.Optional[list[str]] = None
) -> dict:
    record = schemas.ScreeningV2Schema(only=fields).dump(screening)
    assert isinstance(record, dict)  # type guard
    # remove stage field, if present
    record.pop("stage", None)
    # rename study_id field
    if "study_id" in record:
        record["fulltext_id"] = record.pop("study_id")
    # parse dttm values back into python objects
    for field in ("created_at", "updated_at"):
        if field in record:
            record[field] = datetime.datetime.fromisoformat(record[field])
    return record


bp.add_url_rule(
    "/<int:id>/screenings", view_func=FulltextScreeningAPI.as_view("fulltext_screening")
)
bp.add_url_rule(
    "/screenings", view_func=FulltextScreeningsAPI.as_view("fulltext_screenings")
)
