import flask_praetorian
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...extensions import db
from ...lib import constants
from ...models import DataExtraction, Fulltext, FulltextScreening, Review, Study, User
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import ScreeningSchema
from ..swagger import screening_model
from ..utils import assign_status


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
    method_decorators = [flask_praetorian.auth_required]

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
    def get(self, id, fields):
        """get screenings for a single fulltext by id"""
        current_user = flask_praetorian.current_user()
        # check current user authorization
        fulltext = db.session.get(Fulltext, id)
        if not fulltext:
            return not_found_error("<Fulltext(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=fulltext.review_id).one_or_none()
            is None
        ):
            return forbidden_error(
                "{} forbidden to get fulltext screenings for this review".format(
                    current_user
                )
            )
        return ScreeningSchema(many=True, only=fields).dump(fulltext.screenings)

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
    def delete(self, id):
        """delete current app user's screening for a single fulltext by id"""
        current_user = flask_praetorian.current_user()
        # check current user authorization
        fulltext = db.session.get(Fulltext, id)
        if not fulltext:
            return not_found_error("<Fulltext(id={})> not found".format(id))
        if current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return forbidden_error(
                "{} forbidden to delete fulltext screening for this review".format(
                    current_user
                )
            )
        screening = fulltext.screenings.filter_by(user_id=current_user.id).one_or_none()
        if not screening:
            return forbidden_error(
                "{} has not screened {}, so nothing to delete".format(
                    current_user, fulltext
                )
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
    def post(self, args, id):
        """create a screenings for a single fulltext by id"""
        current_user = flask_praetorian.current_user()
        # check current user authorization
        fulltext = db.session.get(Fulltext, id)
        if not fulltext:
            return not_found_error("<Fulltext(id={})> not found".format(id))
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=fulltext.review_id).one_or_none()
            is None
        ):
            return forbidden_error(
                "{} forbidden to screen fulltexts for this review".format(current_user)
            )
        if fulltext.filename is None:
            return forbidden_error(
                "user can't screen {} without first having uploaded its content".format(
                    fulltext
                )
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
        screening = FulltextScreening(
            fulltext.review_id, user_id, id, args["status"], args["exclude_reasons"]
        )
        if fulltext.screenings.filter_by(user_id=current_user.id).one_or_none():
            return forbidden_error(
                "{} has already screened {}".format(current_user, fulltext)
            )
        fulltext.screenings.append(screening)
        db.session.commit()
        current_app.logger.info("inserted %s", screening)
        return ScreeningSchema().dump(screening)

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
    def put(self, args, id):
        """modify current app user's screening of a single fulltext by id"""
        current_user = flask_praetorian.current_user()
        fulltext = db.session.get(Fulltext, id)
        if not fulltext:
            return not_found_error("<Fulltext(id={})> not found".format(id))
        if current_user.is_admin is True and "user_id" in args:
            screening = fulltext.screenings.filter_by(
                user_id=args["user_id"]
            ).one_or_none()
        else:
            screening = fulltext.screenings.filter_by(
                user_id=current_user.id
            ).one_or_none()
        if not screening:
            return not_found_error(
                "{} has not screened this fulltext".format(current_user)
            )
        if args["status"] == "excluded" and not args["exclude_reasons"]:
            return bad_request_error("screenings that exclude must provide a reason")
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(screening, key, value)
        db.session.commit()
        current_app.logger.info("modified %s", screening)
        return ScreeningSchema().dump(screening)


@ns.route("/screenings")
@ns.doc(
    summary="get one or many fulltext screenings",
    produces=["application/json"],
)
class FulltextsScreeningsResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

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
    def get(self, fulltext_id, user_id, review_id, status_counts):
        """get all fulltext screenings by citation, user, or review id"""
        current_user = flask_praetorian.current_user()
        if not any([fulltext_id, user_id, review_id]):
            return bad_request_error(
                "fulltext, user, and/or review id must be specified"
            )
        query = db.session.query(FulltextScreening)
        if fulltext_id is not None:
            # check user authorization
            fulltext = db.session.get(Fulltext, fulltext_id)
            if not fulltext:
                return not_found_error(
                    "<Fulltext(id={})> not found".format(fulltext_id)
                )
            if (
                current_user.is_admin is False
                and fulltext.review.users.filter_by(id=current_user.id).one_or_none()
                is None
            ):
                return forbidden_error(
                    "{} forbidden to get screenings for {}".format(
                        current_user, fulltext
                    )
                )
            query = query.filter_by(fulltext_id=fulltext_id)
        if user_id is not None:
            # check user authorization
            user = db.session.get(User, user_id)
            if not user:
                return not_found_error("<User(id={})> not found".format(user_id))
            if current_user.is_admin is False and not any(
                user_id == user.id
                for review in current_user.reviews
                for user in review.users
            ):
                return forbidden_error(
                    "{} forbidden to get screenings for {}".format(current_user, user)
                )
            query = query.filter_by(user_id=user_id)
        if review_id is not None:
            # check user authorization
            review = db.session.get(Review, review_id)
            if not review:
                return not_found_error("<Review(id={})> not found".format(review_id))
            if (
                current_user.is_admin is False
                and review.users.filter_by(id=current_user.id).one_or_none() is None
            ):
                return forbidden_error(
                    "{} forbidden to get screenings for {}".format(current_user, review)
                )
            query = query.filter_by(review_id=review_id)
        if status_counts is True:
            query = query.with_entities(
                FulltextScreening.status, db.func.count(1)
            ).group_by(FulltextScreening.status)
            return dict(query.all())
        return ScreeningSchema(partial=True, many=True).dump(query.all())

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
    def post(self, args, review_id, user_id):
        """create one or more fulltext screenings (ADMIN ONLY)"""
        current_user = flask_praetorian.current_user()
        if current_user.is_admin is False:
            return forbidden_error("FulltextsScreeningsResource.post is admin-only")
        # check current user authorization
        review = db.session.get(Review, review_id)
        if not review:
            return not_found_error("<Review(id={})> not found".format(review_id))
        # bulk insert fulltext screenings
        screener_user_id = user_id or current_user.id
        screenings_to_insert = []
        for screening in args:
            screening["review_id"] = review_id
            screening["user_id"] = screener_user_id
            screenings_to_insert.append(screening)
        db.session.bulk_insert_mappings(FulltextScreening, screenings_to_insert)
        db.session.commit()
        current_app.logger.info(
            "inserted %s fulltext screenings", len(screenings_to_insert)
        )
        # bulk update fulltext statuses
        num_screeners = review.num_fulltext_screening_reviewers
        fulltext_ids = sorted(s["fulltext_id"] for s in screenings_to_insert)
        # results = db.session.query(FulltextScreening)\
        #     .filter(FulltextScreening.fulltext_id.in_(fulltext_ids))
        # studies_to_update = [
        #     {'id': cid, 'fulltext_status': assign_status(list(scrns), num_screeners)}
        #     for cid, scrns in itertools.groupby(results, attrgetter('fulltext_id'))
        #     ]
        with db.engine.connect() as connection:
            query = """
                SELECT fulltext_id, ARRAY_AGG(status)
                FROM fulltext_screenings
                WHERE fulltext_id IN ({fulltext_ids})
                GROUP BY fulltext_id
                ORDER BY fulltext_id
                """.format(
                fulltext_ids=",".join(str(cid) for cid in fulltext_ids)
            )
            results = connection.execute(sa.text(query))
        studies_to_update = [
            {"id": row[0], "fulltext_status": assign_status(row[1], num_screeners)}
            for row in results
        ]

        db.session.bulk_update_mappings(Study, studies_to_update)
        db.session.commit()
        current_app.logger.info(
            "updated fulltext_status for %s studies", len(studies_to_update)
        )
        # now add data extractions for included fulltexts
        # normally this is done automatically, but not when we're hacking
        # and doing bulk changes to the database
        results = db.session.execute(
            sa.select(Study.id)
            .filter_by(review_id=review_id, fulltext_status="included")
            .filter(~Study.data_extraction.has())
            .order_by(Study.id)
        ).scalars()
        data_extractions_to_insert = [
            {"id": result, "review_id": review_id} for result in results
        ]
        db.session.bulk_insert_mappings(DataExtraction, data_extractions_to_insert)
        db.session.commit()
        current_app.logger.info(
            "inserted %s data extractions", len(data_extractions_to_insert)
        )
        # now update include/exclude counts on review
        status_counts = db.session.execute(
            sa.select(Study.fulltext_status, db.func.count(1))
            .filter_by(review_id=review_id)
            .filter(Study.fulltext_status.in_(["included", "excluded"]))
            .group_by(Study.fulltext_status)
        ).all()
        status_counts = dict(status_counts)
        review.num_fulltexts_included = status_counts.get("included", 0)
        review.num_fulltexts_excluded = status_counts.get("excluded", 0)
        db.session.commit()
        # now update include/exclude counts on review
        status_counts = db.session.execute(
            sa.select(Study.fulltext_status, db.func.count(1))
            .filter_by(review_id=review_id)
            .filter(Study.fulltext_status.in_(["included", "excluded"]))
            .group_by(Study.fulltext_status)
        ).all()
        status_counts = dict(status_counts)
        review.num_fulltexts_included = status_counts.get("included", 0)
        review.num_fulltexts_excluded = status_counts.get("excluded", 0)
        db.session.commit()
