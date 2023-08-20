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
from ...models import Citation, CitationScreening, Fulltext, Review, Study, User
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import ScreeningSchema
from ..swagger import screening_model
from ..utils import assign_status


ns = Namespace(
    "citation_screenings",
    path="/citations",
    description="get, create, delete, modify citation screenings",
)


@ns.route("/<int:id>/screenings")
@ns.doc(
    summary="get, create, delete, and modify data for a single citations's screenings",
    produces=["application/json"],
)
class CitationScreeningsResource(Resource):
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
            200: "successfully got citation screening record(s)",
            403: "current app user forbidden to get citation screening record(s)",
            404: "no citation with matching id was found",
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
        """get screenings for a single citation by id"""
        current_user = flask_praetorian.current_user()
        # check current user authorization
        citation = db.session.get(Citation, id)
        if not citation:
            return not_found_error(f"<Citation(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=citation.review_id).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to get citation screenings for this review"
            )
        current_app.logger.debug("got %s", citation)
        return ScreeningSchema(many=True, only=fields).dump(citation.screenings)

    @ns.doc(
        responses={
            204: "successfully deleted citation screening record",
            403: "current app user forbidden to delete citation screening record",
            404: "no citation with matching id was found",
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
        """delete current app user's screening for a single citation by id"""
        current_user = flask_praetorian.current_user()
        # check current user authorization
        citation = db.session.get(Citation, id)
        if not citation:
            return not_found_error(f"<Citation(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=citation.review_id).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to delete citation screening for this review"
            )
        screening = citation.screenings.filter_by(user_id=current_user.id).one_or_none()
        if not screening:
            return forbidden_error(
                f"{current_user} has not screened {citation}, so nothing to delete"
            )
        db.session.delete(screening)
        db.session.commit()
        current_app.logger.info("deleted %s", screening)
        return "", 204

    @ns.doc(
        expect=(screening_model, "citation screening record to be created"),
        responses={
            200: "citation screening record was created",
            403: "current app user forbidden to create citation screening",
            404: "no citation with matching id was found",
            422: "invalid citation screening record",
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
        """create a screening for a single citation by id"""
        current_user = flask_praetorian.current_user()
        # check current user authorization
        citation = db.session.get(Citation, id)
        if not citation:
            return not_found_error(f"<Citation(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=citation.review_id).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to screen citations for this review"
            )
        # validate and add screening
        if args["status"] == "excluded" and not args["exclude_reasons"]:
            return bad_request_error("screenings that exclude must provide a reason")
        if current_user.is_admin:
            if "user_id" not in args:
                return bad_request_error(
                    "admins must specify 'user_id' when creating a citation screening"
                )
            else:
                user_id = args["user_id"]
        else:
            user_id = current_user.id
        screening = CitationScreening(
            citation.review_id, user_id, id, args["status"], args["exclude_reasons"]
        )
        if citation.screenings.filter_by(user_id=current_user.id).one_or_none():
            return forbidden_error(f"{current_user} has already screened {citation}")
        citation.screenings.append(screening)
        db.session.commit()
        current_app.logger.info("inserted %s", screening)
        return ScreeningSchema().dump(screening)

    @ns.doc(
        expect=(screening_model, "citation screening data to be modified"),
        responses={
            200: "citation screening data was modified",
            401: "current app user not authorized to modify citation screening",
            404: "no citation with matching id was found, or no citation screening exists for current app user",
            422: "invalid modified citation screening data",
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
        """modify current app user's screening of a single citation by id"""
        current_user = flask_praetorian.current_user()
        citation = db.session.get(Citation, id)
        if not citation:
            return not_found_error(f"<Citation(id={id})> not found")
        if current_user.is_admin is True and "user_id" in args:
            screening = citation.screenings.filter_by(
                user_id=args["user_id"]
            ).one_or_none()
        else:
            screening = citation.screenings.filter_by(
                user_id=current_user.id
            ).one_or_none()
        if not screening:
            return not_found_error(f"{current_user} has not screened this citation")
        if args["status"] == "excluded" and not args["exclude_reasons"]:
            return bad_request_error("screenings that exclude must provide a reason")
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(screening, key, value)
        db.session.commit()
        current_app.logger.debug("modified %s", screening)
        return ScreeningSchema().dump(screening)


@ns.route("/screenings")
@ns.doc(
    summary="get one or many citation screenings",
    produces=["application/json"],
)
class CitationsScreeningsResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "citation_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of citation for which to get all citation screenings",
            },
            "user_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of user for which to get all citation screenings",
            },
            "review_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of review for which to get citation screenings",
            },
            "status_counts": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, group screenings by status and return the counts; if False, return the screening records themselves",
            },
        },
        responses={
            200: "successfully got citation screening record(s)",
            400: "bad request: citation_id, user_id, or review_id required",
            403: "current app user forbidden to get citation screening record(s)",
            404: "no citation with matching id was found",
        },
    )
    @use_kwargs(
        {
            "citation_id": ma_fields.Int(
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
    def get(self, citation_id, user_id, review_id, status_counts):
        """get all citation screenings by citation, user, or review id"""
        current_user = flask_praetorian.current_user()
        if not any([citation_id, user_id, review_id]):
            return bad_request_error(
                "citation, user, and/or review id must be specified"
            )
        # TODO: fix this sqlalchemy usage
        query = db.session.query(CitationScreening)
        if citation_id is not None:
            # check user authorization
            citation = db.session.get(Citation, citation_id)
            if not citation:
                return not_found_error(f"<Citation(id={citation_id})> not found")
            if (
                current_user.is_admin is False
                and citation.review.users.filter_by(id=current_user.id).one_or_none()
                is None
            ):
                return forbidden_error(
                    f"{current_user} forbidden to get screenings for {citation}"
                )
            query = query.filter_by(citation_id=citation_id)
        if user_id is not None:
            # check user authorization
            user = db.session.get(User, user_id)
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
            query = query.filter_by(user_id=user_id)
        if review_id is not None:
            # check user authorization
            review = db.session.get(Review, review_id)
            if not review:
                return not_found_error(f"<Review(id={review_id})> not found")
            if (
                current_user.is_admin is False
                and review.users.filter_by(id=current_user.id).one_or_none() is None
            ):
                return forbidden_error(
                    f"{current_user} forbidden to get screenings for {review}"
                )
            query = query.filter_by(review_id=review_id)
        if status_counts is True:
            query = query.with_entities(
                CitationScreening.status, db.func.count(1)
            ).group_by(CitationScreening.status)
            return dict(query.all())
        return ScreeningSchema(partial=True, many=True).dump(query.all())

    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier of review for which to create citation screenings",
            },
            "user_id": {
                "in": "query",
                "type": "integer",
                "description": "unique identifier of user screening citations, if not current app user",
            },
        },
        expect=([screening_model], "citation screening records to create"),
        responses={
            200: "successfully created citation screening record(s)",
            403: "current app user forbidden to create citation screening records",
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
        """create one or more citation screenings (ADMIN ONLY)"""
        current_user = flask_praetorian.current_user()
        if current_user.is_admin is False:
            return forbidden_error("endpoint is admin-only")
        review = db.session.get(Review, review_id)
        if not review:
            return not_found_error(f"<Review(id={review_id})> not found")
        # bulk insert citation screenings
        screener_user_id = user_id or current_user.id
        screenings_to_insert = []
        for screening in args:
            screening["review_id"] = review_id
            screening["user_id"] = screener_user_id
            screenings_to_insert.append(screening)
        db.session.bulk_insert_mappings(CitationScreening, screenings_to_insert)
        db.session.commit()
        current_app.logger.info(
            "inserted %s citation screenings", len(screenings_to_insert)
        )
        # bulk update citation statuses
        num_screeners = review.num_citation_screening_reviewers
        citation_ids = sorted(s["citation_id"] for s in screenings_to_insert)
        # results = db.session.query(CitationScreening)\
        #     .filter(CitationScreening.citation_id.in_(citation_ids))
        # studies_to_update = [
        #     {'id': cid, 'citation_status': assign_status(list(scrns), num_screeners)}
        #     for cid, scrns in itertools.groupby(results, attrgetter('citation_id'))
        #     ]
        with db.engine.connect() as connection:
            query = """
                SELECT citation_id, ARRAY_AGG(status)
                FROM citation_screenings
                WHERE citation_id IN ({citation_ids})
                GROUP BY citation_id
                ORDER BY citation_id
                """.format(
                citation_ids=",".join(str(cid) for cid in citation_ids)
            )
            results = connection.execute(sa.text(query))
        studies_to_update = [
            {"id": row[0], "citation_status": assign_status(row[1], num_screeners)}
            for row in results
        ]

        db.session.bulk_update_mappings(Study, studies_to_update)
        db.session.commit()
        current_app.logger.info(
            "updated citation_status for %s studies", len(studies_to_update)
        )
        # now add fulltexts for included citations
        # normally this is done automatically, but not when we're hacking
        # and doing bulk changes to the database
        results = db.session.execute(
            sa.select(Study.id)
            .filter_by(review_id=review_id, citation_status="included")
            .filter(~Study.fulltext.has())
            .order_by(Study.id)
        ).scalars()
        fulltexts_to_insert = [
            {"id": result, "review_id": review_id} for result in results
        ]
        db.session.bulk_insert_mappings(Fulltext, fulltexts_to_insert)
        db.session.commit()
        current_app.logger.info("inserted %s fulltexts", len(fulltexts_to_insert))
        # now update include/exclude counts on review
        status_counts = db.session.execute(
            sa.select(Study.citation_status, db.func.count(1))
            .filter_by(review_id=review_id, dedupe_status="not_duplicate")
            .filter(Study.citation_status.in_(["included", "excluded"]))
            .group_by(Study.citation_status)
        ).all()
        status_counts = dict(status_counts)
        n_included = status_counts.get("included", 0)
        n_excluded = status_counts.get("excluded", 0)
        review.num_citations_included = n_included
        review.num_citations_excluded = n_excluded
        db.session.commit()
        # do we have to suggest keyterms?
        if n_included >= 25 and n_excluded >= 25:
            from colandr.tasks import suggest_keyterms

            sample_size = min(n_included, n_excluded)
            suggest_keyterms.apply_async(args=[review_id, sample_size])
        # do we have to train a ranking model?
        if n_included >= 100 and n_excluded >= 100:
            from colandr.tasks import train_citation_ranking_model

            train_citation_ranking_model.apply_async(args=[review_id], countdown=30)
