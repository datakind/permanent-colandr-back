import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ... import models
from ...extensions import db
from ...lib import constants
from ...utils import assign_status
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import ScreeningSchema, ScreeningV2Schema
from ..swagger import screening_model


ns = Namespace(
    "fulltext_screenings",
    path="/fulltexts",
    description="get, create, delete, modify fulltext screenings",
)


@ns.route("/<int:id>/screenings")
@ns.doc(
    summary="get, create, delete, and modify data for a single fulltext's screenings",
    produces=["application/json"],
)
class FulltextScreeningsResource(Resource):
    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of screening fields to return",
            },
        },
        responses={
            200: "successfully got fulltext screening record(s)",
            403: "current app user forbidden to get fulltext screening record(s)",
            404: "no fulltext with matching id was found",
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
    @use_kwargs(
        {"fields": DelimitedList(ma_fields.String, delimiter=",", load_default=None)},
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, id, fields):
        """get screenings for a single fulltext by id"""
        current_user = jwtext.get_current_user()
        # check current user authorization
        study = db.session.get(models.Study, id)
        if not study:
            return not_found_error(f"<Study(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.review_user_assoc.filter_by(
                review_id=study.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to get fulltext screenings for this review"
            )
        screenings = study.screenings.filter_by(stage="fulltext")
        # HACK: hide the consolidated (v2) screening schema from this api
        if fields and "fulltext_id" in fields:
            fields.append("study_id")
            fields.remove("fulltext_id")
        screenings_dumped = [
            _convert_screening_v2_into_v1(record)
            for record in ScreeningV2Schema(many=True, only=fields).dump(screenings)
        ]
        return screenings_dumped

    @ns.doc(
        responses={
            204: "successfully deleted fulltext screening record",
            403: "current app user forbidden to delete fulltext screening record; has not screened fulltext, so nothing to delete",
            404: "no fulltext with matching id was found",
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
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        """delete current app user's screening for a single fulltext by id"""
        current_user = jwtext.get_current_user()
        # check current user authorization
        study = db.session.get(models.Study, id)
        if not study:
            return not_found_error(f"<Study(id={id})> not found")
        if (
            current_user.review_user_assoc.filter_by(
                review_id=study.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to delete fulltext screening for this review"
            )
        screening = study.screenings.filter_by(
            stage="fulltext", user_id=current_user.id
        ).one_or_none()
        if not screening:
            return forbidden_error(
                f"{current_user} has not screened {study}, so nothing to delete"
            )
        db.session.delete(screening)
        db.session.commit()
        current_app.logger.info("deleted %s", screening)
        return "", 204

    @ns.doc(
        expect=(screening_model, "fulltext screening record to be created"),
        responses={
            200: "fulltext screening record was created",
            403: "current app user forbidden to create fulltext screening; has already created a screening for this fulltext, or no screening can be created because the full-text has not yet been uploaded",
            404: "no fulltext with matching id was found",
            422: "invalid fulltext screening record",
        },
    )
    @use_args(ScreeningSchema(partial=["user_id", "review_id"]), location="json")
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @jwtext.jwt_required()
    def post(self, args, id):
        """create a screenings for a single fulltext by id"""
        current_user = jwtext.get_current_user()
        # check current user authorization
        study = db.session.get(models.Study, id)
        if not study:
            return not_found_error(f"<Fulltext(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.review_user_assoc.filter_by(
                review_id=study.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to screen fulltexts for this review"
            )
        if not study.fulltext:
            return forbidden_error(
                f"user can't screen {study} without first having uploaded its content"
            )
        # validate and add screening
        if args["status"] == "excluded" and not args["exclude_reasons"]:
            return bad_request_error("screenings that exclude must provide a reason")
        if current_user.is_admin:
            if "user_id" not in args:
                return bad_request_error(
                    "admins must specify 'user_id' when creating a fulltext screening"
                )
            else:
                user_id = args["user_id"]
        else:
            user_id = current_user.id
        screening = models.Screening(
            user_id,
            study.review_id,
            id,
            "fulltext",
            args["status"],
            args["exclude_reasons"],
        )
        if study.screenings.filter_by(
            stage="fulltext", user_id=current_user.id
        ).one_or_none():
            return forbidden_error(f"{current_user} has already screened {study}")
        study.screenings.append(screening)
        db.session.commit()
        current_app.logger.info("inserted %s", screening)
        return _convert_screening_v2_into_v1(ScreeningV2Schema().dump(screening))

    @ns.doc(
        expect=(screening_model, "fulltext screening data to be modified"),
        responses={
            200: "fulltext screening data was modified",
            403: "current app user forbidden to modify fulltext screening",
            404: "no fulltext with matching id was found, or no fulltext screening exists for current app user",
            422: "invalid modified fulltext screening data",
        },
    )
    @use_args(
        ScreeningSchema(
            only=["user_id", "status", "exclude_reasons"],
            partial=["status", "exclude_reasons"],
        ),
        location="json",
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @jwtext.jwt_required()
    def put(self, args, id):
        """modify current app user's screening of a single fulltext by id"""
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)
        if not study:
            return not_found_error(f"<Study(id={id})> not found")
        if current_user.is_admin is True and "user_id" in args:
            screening = study.screenings.filter_by(
                stage="fulltext", user_id=args["user_id"]
            ).one_or_none()
        else:
            screening = study.screenings.filter_by(
                stage="fulltext", user_id=current_user.id
            ).one_or_none()
        if not screening:
            return not_found_error(f"{current_user} has not screened this fulltext")
        if args["status"] == "excluded" and not args["exclude_reasons"]:
            return bad_request_error("screenings that exclude must provide a reason")
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(screening, key, value)
        db.session.commit()
        current_app.logger.info("modified %s", screening)
        return _convert_screening_v2_into_v1(ScreeningV2Schema().dump(screening))


@ns.route("/screenings")
@ns.doc(
    summary="get one or many fulltext screenings",
    produces=["application/json"],
)
class FulltextsScreeningsResource(Resource):
    @ns.doc(
        params={
            "fulltext_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of fulltext for which to get all fulltext screenings",
            },
            "user_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of user for which to get all fulltext screenings",
            },
            "review_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of review for which to get fulltext screenings",
            },
            "status_counts": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, group screenings by status and return the counts; if False, return the screening records themselves",
            },
        },
        responses={
            200: "successfully got fulltext screening record(s)",
            400: "bad request: fulltext_id, user_id, or review_id required",
            403: "current app user forbidden to get fulltext screening record(s)",
            404: "no fulltext with matching id was found",
        },
    )
    @use_kwargs(
        {
            "fulltext_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
            "user_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "review_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "status_counts": ma_fields.Boolean(load_default=False),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, fulltext_id, user_id, review_id, status_counts):
        """get all fulltext screenings by citation, user, or review id"""
        current_user = jwtext.get_current_user()
        if not any([fulltext_id, user_id, review_id]):
            return bad_request_error(
                "fulltext, user, and/or review id must be specified"
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
                return not_found_error(f"<Study(id={fulltext_id})> not found")
            if (
                current_user.is_admin is False
                and study.review.review_user_assoc.filter_by(
                    user_id=current_user.id
                ).one_or_none()
                is None
            ):
                return forbidden_error(
                    f"{current_user} forbidden to get screenings for {study}"
                )
            stmt = stmt.where(models.Screening.study_id == fulltext_id)
        if user_id is not None:
            # check user authorization
            user = db.session.get(models.User, user_id)
            if not user:
                return not_found_error(f"<User(id={user_id})> not found")
            if current_user.is_admin is False and not any(
                user_id == user.id
                for review in current_user.reviews
                for user in review.users
            ):
                return forbidden_error(
                    f"{current_user} forbidden to get screenings for {user}"
                )
            stmt = stmt.where(models.Screening.user_id == user_id)
        if review_id is not None:
            # check user authorization
            review = db.session.get(models.Review, review_id)
            if not review:
                return not_found_error(f"<Review(id={review_id})> not found")
            if (
                current_user.is_admin is False
                and review.review_user_assoc.filter_by(
                    user_id=current_user.id
                ).one_or_none()
                is None
            ):
                return forbidden_error(
                    f"{current_user} forbidden to get screenings for {review}"
                )
            stmt = stmt.where(models.Screening.review_id == review_id)

        if status_counts is True:
            stmt = stmt.group_by(models.Screening.status)
            return {row.status: row.count for row in db.session.execute(stmt)}
        else:
            results = db.session.execute(stmt).scalars()
            return [
                _convert_screening_v2_into_v1(record)
                for record in ScreeningV2Schema(partial=True, many=True).dump(results)
            ]

    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier of review for which to create fulltext screenings",
            },
            "user_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of user screening fulltexts, if not current app user",
            },
        },
        expect=([screening_model], "fulltext screening records to create"),
        responses={
            200: "successfully created fulltext screening record(s)",
            403: "current app user forbidden to create fulltext screening records",
            404: "no review with matching id was found",
        },
    )
    @use_args(
        ScreeningSchema(many=True, partial=["user_id", "review_id"]), location="json"
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "user_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="query",
    )
    @jwtext.jwt_required()
    def post(self, args, review_id, user_id):
        """create one or more fulltext screenings (ADMIN ONLY)"""
        current_user = jwtext.get_current_user()
        if current_user.is_admin is False:
            return forbidden_error("FulltextsScreeningsResource.post is admin-only")
        # check current user authorization
        review = db.session.get(models.Review, review_id)
        if not review:
            return not_found_error(f"<Review(id={review_id})> not found")
        # bulk insert fulltext screenings
        screener_user_id = user_id or current_user.id
        screenings_to_insert = []
        for screening in args:
            screening["user_id"] = screener_user_id
            screening["review_id"] = review_id
            screening["stage"] = "fulltext"
            screenings_to_insert.append(screening)
        db.session.execute(sa.insert(models.Screening), screenings_to_insert)
        db.session.commit()
        current_app.logger.info(
            "inserted %s fulltext screenings", len(screenings_to_insert)
        )
        # bulk update fulltext statuses
        num_screeners = review.num_fulltext_screening_reviewers
        study_ids = sorted(s["study_id"] for s in screenings_to_insert)
        # results = db.session.query(models.Screening)\
        #     .filter(models.Screening.study_id.in_(study_ids))
        # studies_to_update = [
        #     {'id': cid, 'fulltext_status': assign_status(list(scrns), num_screeners)}
        #     for cid, scrns in itertools.groupby(results, attrgetter('fulltext_id'))
        #     ]
        with db.engine.connect() as connection:
            query = """
                SELECT study_id, ARRAY_AGG(status)
                FROM screenings
                WHERE study_id IN ({study_ids})
                GROUP BY study_id
                ORDER BY study_id
                """.format(study_ids=",".join(str(cid) for cid in study_ids))
            results = connection.execute(sa.text(query))
        studies_to_update = [
            {"id": row[0], "fulltext_status": assign_status(row[1], num_screeners)}
            for row in results
        ]

        db.session.execute(sa.update(models.Study), studies_to_update)
        db.session.commit()
        current_app.logger.info(
            "updated fulltext_status for %s studies", len(studies_to_update)
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
            "inserted %s data extractions", len(data_extractions_to_insert)
        )
        # now update include/exclude counts on review
        status_counts_stmt = (
            sa.select(models.Study.fulltext_status, db.func.count(1))
            .filter_by(review_id=review_id, dedupe_status="not_duplicate")
            # .filter(models.Study.fulltext_status.in_(["included", "excluded"]))
            .filter(models.Study.fulltext_status == sa.any_(["included", "excluded"]))
            .group_by(models.Study.fulltext_status)
        )
        status_counts: dict[str, int] = {
            row.fulltext_status: row.count
            for row in db.session.execute(status_counts_stmt)
        }  # type: ignore
        review.num_fulltexts_included = status_counts.get("included", 0)
        review.num_fulltexts_excluded = status_counts.get("excluded", 0)
        db.session.commit()


def _convert_screening_v2_into_v1(record) -> dict:
    # remove stage field, if present
    record.pop("stage", None)
    # rename study_id field to citation_id
    try:
        record["fulltext_id"] = record.pop("study_id")
    except KeyError:
        pass
    return record
