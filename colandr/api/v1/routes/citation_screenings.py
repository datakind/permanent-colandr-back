import datetime
import typing as t

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models, tasks
from ....extensions import db
from .. import authz, errors, schemas


bp = af.APIBlueprint("citation_screenings", __name__, url_prefix="/citations")


class CitationScreeningAPI(MethodView):
    @bp.doc(
        summary="get screenings for a single citation",
        responses={
            200: "successfully got citation screening(s)",
            403: "current app user forbidden to get citation screening(s)",
            404: "no citation matching id was found",
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

        if not authz.user_is_allowed_for_review(current_user, study.review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get citation screenings for this review"
            )

        screenings = db.session.execute(
            study.screenings.select().filter_by(stage="citation")
        ).scalars()
        if not screenings:
            raise errors.NotFoundError(
                message=f"no screenings for <Study(id={id})> found"
            )

        # HACK: hide the consolidated (v2) screening schema from this api
        if fields and "citation_id" in fields:
            fields.append("study_id")
            fields.remove("citation_id")
        results = [
            _convert_screening_v2_into_v1(screening, fields) for screening in screenings
        ]
        current_app.logger.debug(
            "%s got %s screenings for %s", current_user, len(results), study
        )
        return results

    @bp.doc(
        summary="create a screening for a single citation",
        responses={
            200: "citation screening record was created",
            400: "citation screening was invalid",
            403: "current app user forbidden to create citation screening",
            404: "no citation with matching id was found",
            422: "invalid citation screening record",
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
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if not authz.user_is_allowed_for_review(
            current_user, study.review_id, if_frozen=False
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to screen citations for this review"
            )

        # validate and add screening
        if json_data["status"] == "excluded" and not json_data["exclude_reasons"]:
            raise errors.BadRequestError(
                message="screenings that exclude must provide a reason"
            )

        if current_user.is_admin:
            if "user_id" not in json_data:
                raise errors.BadRequestError(
                    message="admins must specify 'user_id' when creating a citation screening"
                )
            else:
                user_id = json_data["user_id"]
        else:
            user_id = current_user.id

        if db.session.execute(
            study.screenings.select().filter_by(stage="citation", user_id=user_id)
        ).one_or_none():
            raise errors.ForbiddenError(
                message=f"{current_user} has already screened {study}"
            )

        screening = models.Screening(
            user_id=user_id,
            review_id=study.review_id,
            study_id=id,
            stage="citation",
            status=json_data["status"],
            exclude_reasons=json_data["exclude_reasons"],
        )
        study.screenings.add(screening)
        db.session.commit()

        current_app.logger.info("%s created %s", current_user, screening)
        tasks.train_study_ranker_model.apply_async(args=[study.review_id, screening.id])
        return _convert_screening_v2_into_v1(screening)

    @bp.doc(
        summary="modify a screening for a single citation",
        responses={
            200: "citation screening data was modified",
            401: "current app user not authorized to modify citation screening",
            404: "no citation matching id was found, or no citation screening exists for current app user",
            422: "invalid modified citation screening data",
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
                    stage="citation", user_id=json_data["user_id"]
                )
            ).scalar_one_or_none()
        else:
            screening = db.session.execute(
                study.screenings.select().filter_by(
                    stage="citation", user_id=current_user.id
                )
            ).scalar_one_or_none()
        if not screening:
            raise errors.NotFoundError(
                message=f"{current_user} has not screened this citation"
            )

        if json_data["status"] == "excluded" and not json_data.get("exclude_reasons"):
            raise errors.BadRequestError(
                message="screenings that exclude must provide a reason"
            )

        for key, value in json_data.items():
            setattr(screening, key, value)
        db.session.commit()

        current_app.logger.info("%s modified %s", current_user, screening)
        return _convert_screening_v2_into_v1(screening)

    @bp.doc(
        summary="delete current app user's screening for a single citation",
        responses={
            204: "successfully deleted citation screening record",
            403: "current app user forbidden to delete citation screening record",
            404: "no citation with matching id was found",
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

        if not authz.user_is_allowed_for_review(
            current_user, study.review_id, if_frozen=False
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to delete citation screening for this review"
            )

        screening = db.session.execute(
            study.screenings.select().filter_by(
                stage="citation", user_id=current_user.id
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


class CitationScreeningsAPI(MethodView):
    @bp.doc(
        summary="get citation screenings by citation, user, or review id",
        responses={
            200: "successfully got citation screening record(s)",
            400: "bad request: citation_id, user_id, or review_id required",
            403: "current app user forbidden to get citation screening record(s)",
            404: "no citation with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "citation_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of citation for which to get all citation screenings"
                },
            ),
            "user_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of user for which to get all citation screenings"
                },
            ),
            "review_id": af.fields.Integer(
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of review for which to get citation screenings"
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
        citation_id = query_data.get("citation_id")
        user_id = query_data.get("user_id")
        review_id = query_data.get("review_id")
        status_counts = query_data.get("status_counts")
        current_user = jwtext.get_current_user()

        if not any([citation_id, user_id, review_id]):
            raise errors.BadRequestError(
                message="citation, user, and/or review id must be specified"
            )

        stmt = (
            sa.select(models.Screening)
            if status_counts is False
            else sa.select(models.Screening.status, db.func.count(1))
        )
        stmt = stmt.where(models.Screening.stage == "citation")
        if citation_id is not None:
            # check user authorization
            study = db.session.get(models.Study, citation_id)
            if not study:
                raise errors.NotFoundError(
                    message=f"<Study(id={citation_id})> not found"
                )
            if not authz.user_is_allowed_for_review(current_user, study.review_id):
                raise errors.ForbiddenError(
                    message=f"{current_user} forbidden to get screenings for {study}"
                )
            stmt = stmt.where(models.Screening.study_id == citation_id)
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
                and db.session.execute(
                    review.review_user_assoc.filter_by(user_id=current_user.id)
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


bp.add_url_rule(
    "/<int:id>/screenings", view_func=CitationScreeningAPI.as_view("citation_screening")
)
bp.add_url_rule(
    "/screenings", view_func=CitationScreeningsAPI.as_view("citation_screenings")
)


def _convert_screening_v2_into_v1(
    screening: models.Screening, fields: t.Optional[list[str]] = None
) -> dict:
    record = schemas.ScreeningV2Schema(only=fields).dump(screening)
    assert isinstance(record, dict)  # type guard
    # remove stage field, if present
    record.pop("stage", None)
    # rename study_id field to citation_id
    if "study_id" in record:
        record["citation_id"] = record.pop("study_id")
    # parse dttm values back into python objects
    for field in ("created_at", "updated_at"):
        if field in record:
            record[field] = datetime.datetime.fromisoformat(record[field])
    return record
