import flask_praetorian
from flask import current_app, g
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from marshmallow import fields as ma_fields
from marshmallow.validate import URL, Length, OneOf, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants
from ...models import Citation, DataSource, Review, Study, db
from ..errors import forbidden_error, not_found_error, validation_error
from ..schemas import CitationSchema, DataSourceSchema
from ..swagger import citation_model


ns = Namespace(
    "citations", path="/citations", description="get, delete, update citations"
)


@ns.route("/<int:id>")
@ns.doc(
    summary="get, delete, and modify data for single citations",
    produces=["application/json"],
)
class CitationResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "fields": {
                "in": "query",
                "type": "string",
                "description": "comma-delimited list-as-string of citation fields to return",
            },
        },
        responses={
            200: "successfully got citation record",
            403: "current app user forbidden to get citation record",
            404: "no citation with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True,
                location="view_args",
                validate=Range(min=1, max=constants.MAX_BIGINT),
            ),
            "fields": DelimitedList(ma_fields.String, delimiter=",", missing=None),
        }
    )
    def get(self, id, fields):
        """get record for a single citation by id"""
        citation = db.session.query(Citation).get(id)
        if not citation:
            return not_found_error("<Citation(id={})> not found".format(id))
        if (
            g.current_user.is_admin is False
            and citation.review.users.filter_by(id=g.current_user.id).one_or_none()
            is None
        ):
            return forbidden_error(
                "{} forbidden to get this citation".format(g.current_user)
            )
        if fields and "id" not in fields:
            fields.append("id")
        current_app.logger.debug("got %s", citation)
        return CitationSchema(only=fields).dump(citation)

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        responses={
            200: "request was valid, but record not deleted because `test=False`",
            204: "successfully deleted citation record",
            403: "current app user forbidden to delete citation record",
            404: "no citation with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True,
                location="view_args",
                validate=Range(min=1, max=constants.MAX_BIGINT),
            ),
            "test": ma_fields.Boolean(missing=False),
        }
    )
    def delete(self, id, test):
        """delete record for a single citation by id"""
        citation = db.session.query(Citation).get(id)
        if not citation:
            return not_found_error("<Citation(id={})> not found".format(id))
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return forbidden_error(
                "{} forbidden to delete this citation".format(g.current_user)
            )
        db.session.delete(citation)
        if test is False:
            db.session.commit()
            current_app.logger.info("deleted %s", citation)
            return "", 204
        else:
            db.session.rollback()
            return "", 200

    @ns.doc(
        params={
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        body=(citation_model, "citation data to be modified"),
        responses={
            200: "citation data was modified (if test = False)",
            403: "current app user forbidden to modify citation",
            404: "no citation with matching id was found",
        },
    )
    @use_args(CitationSchema(partial=True))
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True,
                location="view_args",
                validate=Range(min=1, max=constants.MAX_BIGINT),
            ),
            "test": ma_fields.Boolean(missing=False),
        }
    )
    def put(self, args, id, test):
        """modify record for a single citation by id"""
        citation = db.session.query(Citation).get(id)
        if not citation:
            return not_found_error("<Citation(id={})> not found".format(id))
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return forbidden_error(
                "{} forbidden to modify this citation".format(g.current_user)
            )
        for key, value in args.items():
            if key is missing or key == "other_fields":
                continue
            else:
                setattr(citation, key, value)
        if test is False:
            db.session.commit()
            current_app.logger.info("modified %s", citation)
        else:
            db.session.rollback()
        return CitationSchema().dump(citation)


@ns.route("")
@ns.doc(
    summary="create a single citation",
    produces=["application/json"],
)
class CitationsResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier for review for which a citation will be created",
            },
            "source_type": {
                "in": "query",
                "type": "string",
                "enum": ["database", "gray literature"],
                "description": "type of source through which citation was found",
            },
            "source_name": {
                "in": "query",
                "type": "string",
                "description": "name of source through which citation was found",
            },
            "source_url": {
                "in": "query",
                "type": "string",
                "format": "url",
                "description": "url of source through which citation was found",
            },
            "status": {
                "in": "query",
                "type": "string",
                "enum": ["not_screened", "included", "excluded"],
                "description": "known screening status of citation, if anything",
            },
            "test": {
                "in": "query",
                "type": "boolean",
                "default": False,
                "description": "if True, request will be validated but no data will be affected",
            },
        },
        responses={
            200: "successfully created citation record",
            403: "current app user forbidden to create citation for this review",
            404: "no review with matching id was found",
        },
    )
    @use_args(CitationSchema(partial=True))
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "source_type": ma_fields.Str(
                required=True, validate=OneOf(["database", "gray literature"])
            ),
            "source_name": ma_fields.Str(missing=None, validate=Length(max=100)),
            "source_url": ma_fields.Str(
                missing=None, validate=[URL(relative=False), Length(max=500)]
            ),
            "status": ma_fields.Str(
                missing=None, validate=OneOf(["not_screened", "included", "excluded"])
            ),
            "test": ma_fields.Boolean(missing=False),
        }
    )
    def post(self, args, review_id, source_type, source_name, source_url, status, test):
        """create a single citation"""
        review = db.session.query(Review).get(review_id)
        if not review:
            return not_found_error("<Review(id={})> not found".format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return forbidden_error(
                "{} forbidden to add citations to this review".format(g.current_user)
            )
        # upsert the data source
        try:
            DataSourceSchema().validate(
                {
                    "source_type": source_type,
                    "source_name": source_name,
                    "source_url": source_url,
                }
            )
        except ValidationError as e:
            return validation_error(e.messages)
        data_source = (
            db.session.query(DataSource)
            .filter_by(source_type=source_type, source_name=source_name)
            .one_or_none()
        )
        if data_source is None:
            data_source = DataSource(source_type, source_name, source_url=source_url)
            db.session.add(data_source)
        if test is False:
            db.session.commit()
            current_app.logger.info("inserted %s", data_source)
        else:
            db.session.rollback()
            return ""

        # add the study
        study = Study(g.current_user.id, review_id, data_source.id)
        if status is not None:
            study.citation_status = status
        db.session.add(study)
        db.session.commit()

        # *now* add the citation
        citation = args
        citation = CitationSchema().load(citation)  # this sanitizes the data
        citation = Citation(study.id, **citation)
        db.session.add(citation)
        db.session.commit()
        current_app.logger.info("inserted %s", citation)

        # TODO: what about deduplication?!
        # TODO: what about adding *multiple* citations via this endpoint?

        return CitationSchema().dump(citation)
