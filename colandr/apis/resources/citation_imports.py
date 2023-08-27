import flask_praetorian
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import ValidationError
from marshmallow import fields as ma_fields
from marshmallow.validate import URL, Length, OneOf, Range
from webargs.flaskparser import use_kwargs
from werkzeug.utils import secure_filename

from ... import tasks
from ...extensions import db
from ...lib import constants, preprocessors
from ...models import Citation, DataSource, Fulltext, Import, Review, Study
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import DataSourceSchema, ImportSchema


ns = Namespace(
    "citation_imports",
    path="/citations/imports",
    description="import citations in bulk and get import history",
)


@ns.route("")
@ns.doc(
    summary="import citations in bulk and get import history",
    produces=["application/json"],
)
class CitationsImportsResource(Resource):
    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier of review for which citations were imported",
            },
        },
        responses={
            200: "successfully got citation import history",
            403: "current app user forbidden to get citation import history",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            )
        },
        location="query",
    )
    def get(self, review_id):
        """get citation import history for a review"""
        current_user = flask_praetorian.current_user()
        review = db.session.get(Review, review_id)
        if not review:
            return not_found_error(f"<Review(id={review_id})> not found")
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=review_id).one_or_none() is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to add citations to this review"
            )
        results = review.imports.filter_by(record_type="citation")
        return ImportSchema(many=True).dump(results.all())

    @ns.doc(
        params={
            "uploaded_file": {
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "file containing one or many citations in a standard format (.ris or .bib)",
            },
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": True,
                "description": "unique identifier for review for which citations will be imported",
            },
            "source_type": {
                "in": "query",
                "type": "string",
                "enum": ["database", "gray literature"],
                "description": "type of source through which citations were found",
            },
            "source_name": {
                "in": "query",
                "type": "string",
                "description": "name of source through which citations were found",
            },
            "source_url": {
                "in": "query",
                "type": "string",
                "format": "url",
                "description": "url of source through which citations were found",
            },
            "status": {
                "in": "query",
                "type": "string",
                "enum": ["not_screened", "included", "excluded"],
                "description": "known screening status of citations, if anything",
            },
            "dedupe": {
                "in": "query",
                "type": "boolean",
                "default": True,
                "description": "if True, all review citations will be (re-)deduped",
            },
        },
        responses={
            200: "successfully imported citations in bulk",
            403: "current app user forbidden to import citations for this review",
            404: "no review with matching id was found",
        },
    )
    @use_kwargs({"uploaded_file": ma_fields.Raw(required=True)}, location="files")
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
            "source_type": ma_fields.Str(
                required=True, validate=OneOf(["database", "gray literature"])
            ),
            "source_name": ma_fields.Str(load_default=None, validate=Length(max=100)),
            "source_url": ma_fields.Str(
                load_default=None, validate=[URL(relative=False), Length(max=500)]
            ),
            "status": ma_fields.Str(
                load_default=None,
                validate=OneOf(["not_screened", "included", "excluded"]),
            ),
            "dedupe": ma_fields.Boolean(load_default=True),
        },
        location="query",
    )
    def post(
        self,
        uploaded_file,
        review_id,
        source_type,
        source_name,
        source_url,
        status,
        dedupe,
    ):
        """import citations in bulk for a review"""
        current_user = flask_praetorian.current_user()
        review = db.session.get(Review, review_id)
        if not review:
            return not_found_error(f"<Review(id={review_id})> not found")
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(id=review_id).one_or_none() is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to add citations to this review"
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
            return bad_request_error(e.messages)
        data_source = db.session.execute(
            sa.select(DataSource).filter_by(
                source_type=source_type, source_name=source_name
            )
        ).scalar_one_or_none()
        if data_source is None:
            data_source = DataSource(source_type, source_name, source_url=source_url)
            db.session.add(data_source)
        db.session.commit()
        current_app.logger.info("inserted %s", data_source)
        data_source_id = data_source.id

        # TODO: see about using secure_filename(uploaded_file.filename)
        fname = uploaded_file.filename
        try:
            citations_to_insert = preprocessors.preprocess_citations(
                uploaded_file.stream, fname, review_id
            )
        except ValueError as e:
            current_app.logger.exception(str(e))
            return bad_request_error(str(e))

        n_citations = len(citations_to_insert)

        user_id = current_user.id
        if status is None:
            studies_to_insert = [
                {
                    "user_id": user_id,
                    "review_id": review_id,
                    "data_source_id": data_source_id,
                }
                for i in range(n_citations)
            ]
        else:
            studies_to_insert = [
                {
                    "user_id": user_id,
                    "review_id": review_id,
                    "data_source_id": data_source_id,
                    "citation_status": status,
                }
                for i in range(n_citations)
            ]

        # insert studies, and get their primary keys _back_
        stmt = sa.insert(Study).values(studies_to_insert).returning(Study.id)
        with db.engine.connect() as conn:
            study_ids = [result[0] for result in conn.execute(stmt)]

        # add study ids to citations as their primary keys
        # then bulk insert as mappings
        # this method is required because not all citations have all fields
        for study_id, citation in zip(study_ids, citations_to_insert):
            citation["id"] = study_id
        db.session.bulk_insert_mappings(Citation, citations_to_insert)

        # if citations' status is "included", we have to bulk insert
        # the corresponding fulltexts, since bulk operations won't trigger
        # the fancy events defined in models.py
        if status == "included":
            with db.engine.connect() as conn:
                conn.execute(
                    Fulltext.__table__.insert(),
                    [
                        {"id": study_id, "review_id": review_id}
                        for study_id in study_ids
                    ],
                )

        # don't forget about a record of the import
        citations_import = Import(
            review_id, user_id, data_source_id, "citation", n_citations, status=status
        )
        db.session.add(citations_import)
        db.session.commit()
        current_app.logger.info(
            'imported %s citations from file "%s" into %s', n_citations, fname, review
        )

        # lastly, don't forget to deduplicate the citations and get their word2vecs
        tasks.get_citations_text_content_vectors.apply_async(
            args=[review_id], countdown=3
        )
        if dedupe is True:
            tasks.deduplicate_citations.apply_async(args=[review_id], countdown=3)
