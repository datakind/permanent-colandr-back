import io
import os
import pathlib
import typing as t

import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView
from werkzeug.utils import secure_filename

from .... import models, tasks
from ....extensions import db, limiter
from ....lib import fileio
from .. import authz, errors, schemas


bp = af.APIBlueprint("citation_imports", __name__, url_prefix="/citations/imports")


class CitationImportsPostSchema(schemas.DataSourceSchema):
    review_id = af.fields.Integer(
        required=True,
        validate=af.validators.Range(min=1),
        metadata={
            "description": "unique identifier for review for which citations will be imported"
        },
    )
    status = af.fields.String(
        validate=af.validators.OneOf(["not_screened", "included", "excluded"]),
        metadata={"description": "known screening status of citations, if anything"},
    )
    dedupe = af.fields.Boolean(
        load_default=True,
        metadata={"description": "if True, all review citations will be (re-)deduped"},
    )


class CitationImportsAPI(MethodView):
    @bp.doc(
        summary="get citation import history for a review",
        responses={
            200: "successfully got citation import history",
            403: "current app user forbidden to get citation import history",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "review_id": af.fields.Integer(
                required=True,
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier of review for which citations were imported"
                },
            )
        },
        location="query",
    )
    @bp.output(schemas.ImportSchema(many=True))
    @jwtext.jwt_required()
    def get(self, query_data):
        review_id = query_data["review_id"]
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(current_user, review_id):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get citation imports for this review"
            )

        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        result = db.session.execute(
            review.imports.select().filter_by(record_type="citation")
        )
        citation_imports = result.scalars().all()

        current_app.logger.info(
            "%s got %s citation imports for %s",
            current_user,
            len(citation_imports),
            review,
        )
        return citation_imports

    @bp.doc(
        summary="import citations in bulk for a review",
        responses={
            200: "successfully imported citations in bulk",
            403: "current app user forbidden to import citations for this review",
            404: "no review with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "uploaded_file": af.fields.File(
                required=True,
                metadata={
                    "description": "file containing one or many citations in a standard format (.ris or .bib)"
                },
            )
        },
        location="files",
    )
    @bp.input(CitationImportsPostSchema, location="query")
    @bp.output({})
    @jwtext.jwt_required()
    def post(self, files_data, query_data):
        uploaded_file = files_data["uploaded_file"]
        review_id = query_data["review_id"]
        source_type = query_data["source_type"]
        source_name = query_data.get("source_name")
        source_url = query_data.get("source_url")
        status = query_data.get("status")
        dedupe = query_data["dedupe"]
        current_user = jwtext.get_current_user()
        if not authz.user_is_allowed_for_review(
            current_user, review_id, if_frozen=False
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to add citations to this review"
            )

        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        data_source = db.session.execute(
            sa.select(models.DataSource).filter_by(
                source_type=source_type, source_name=source_name
            )
        ).scalar_one_or_none()
        if data_source is None:
            data_source = models.DataSource(
                source_type=source_type, source_name=source_name, source_url=source_url
            )
            db.session.add(data_source)
        db.session.commit()

        current_app.logger.info("inserted %s", data_source)
        data_source_id = data_source.id

        # properly validate uploaded file names/exts
        fname = secure_filename(uploaded_file.filename)
        _, fext = os.path.splitext(fname)
        if fext not in current_app.config["ALLOWED_CITATION_UPLOAD_EXTENSIONS"]:
            raise errors.BadRequestError(
                message=f"received invalid file type for citation import: '{fext}'"
            )

        # unfortunately, we need to read the full file into memory rather than streaming
        # so we can preprocess the citations and later save the raw file to disk
        uploaded_data = uploaded_file.stream.read()

        try:
            citations_to_insert = _preprocess_citations(
                io.BytesIO(uploaded_data), fname, review_id
            )
        except ValueError as e:
            current_app.logger.exception(str(e))
            raise errors.BadRequestError(message=str(e))

        n_citations = len(citations_to_insert)

        user_id = current_user.id
        if status is None:
            studies_to_insert = [
                {
                    "user_id": user_id,
                    "review_id": review_id,
                    "data_source_id": data_source_id,
                    "citation": citation,
                }
                for citation in citations_to_insert
            ]
        else:
            studies_to_insert = [
                {
                    "user_id": user_id,
                    "review_id": review_id,
                    "data_source_id": data_source_id,
                    "citation": citation,
                    "citation_status": status,
                }
                for citation in citations_to_insert
            ]

        # insert studies
        db.session.execute(sa.insert(models.Study), studies_to_insert)
        # as well as a record of the import
        citations_import = models.Import(
            review_id=review_id,
            user_id=user_id,
            data_source_id=data_source_id,
            record_type="citation",
            num_records=n_citations,
            status=status,
        )
        db.session.add(citations_import)
        db.session.commit()
        current_app.logger.info(
            '%s imported %s citations from file "%s" into %s',
            current_user,
            n_citations,
            fname,
            review,
        )

        fs = current_app.extensions["filesystem"]
        # assign filename based an id, and full path
        filename = f"{citations_import.id}{fext}"
        filepath = os.path.join(
            current_app.config["CITATION_UPLOADS_DIR"],
            f"review_{review_id:08}",
            filename,
        )
        # make review directory if doesn't already exist
        fs.makedirs(os.path.dirname(filepath), exist_ok=True)
        # save content to file on filesystem
        with fs.open(filepath, mode="wb") as f:
            # uploaded_file.save(f) may also work well
            f.write(uploaded_data)

        # lastly, don't forget to deduplicate the citations and get their word2vecs
        tasks.get_citations_text_content_vectors.apply_async(
            args=[review_id], countdown=3
        )
        if dedupe is True:
            tasks.deduplicate_citations.apply_async(args=[review_id], countdown=3)


# NOTE: flask-limiter doesn't behave when applied to routes via MethodView.decorators
# this is an ugly but serviceable work-around
# citation_imports_api_view_func = CitationImportsAPI.as_view("citation_imports")
# citation_imports_api_view_func = limiter.limit("1 per 5 seconds", methods=["POST"])(
#     citation_imports_api_view_func
# )
# bp.add_url_rule("/", view_func=citation_imports_api_view_func)
# NOTE: flask-limiter actually just doesn't work with this API for some reason
# let's not rate-limit it, and instead kick the can down the road
bp.add_url_rule("/", view_func=CitationImportsAPI.as_view("citation_imports"))


def _preprocess_citations(
    path_or_stream: str | pathlib.Path | t.IO[bytes], fname: str, review_id: int
) -> list[dict]:
    _, fext = os.path.splitext(fname)
    reader = (
        fileio.studies.RisReader()
        if fext in (".ris", ".txt")
        else fileio.studies.BibTexReader()
        if fext == ".bib"
        else fileio.studies.TabularReader(delimiter=",")
        if fext == ".csv"
        else fileio.studies.TabularReader(delimiter="\t")
        if fext == ".tsv"
        else None
    )
    # NOTE: we already check file extension in API, so this should never happen
    assert reader is not None

    try:
        records = reader.sanitize(reader.read(path_or_stream))
    except Exception:
        raise ValueError(f"unable to parse citations import file: '{fname}'")

    schema = schemas.CitationSchema(partial=True, unknown="include")
    declared_fields = schema.declared_fields
    citations = []
    for record in records:
        record["review_id"] = review_id
        citation = {
            key: value for key, value in record.items() if key in declared_fields
        }
        citation["other_fields"] = {
            key: value for key, value in record.items() if key not in declared_fields
        }
        try:
            citation = schema.load(record)
        except Exception as e:
            current_app.logger.warning(
                "citation not compliant with schema; skipping... %s", e
            )
            continue
        citations.append(citation)

    return citations
