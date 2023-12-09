import io
import os

import flask_jwt_extended as jwtext
import ftfy
from flask import current_app, send_from_directory
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs
from werkzeug.utils import secure_filename

from ... import tasks
from ...extensions import db
from ...lib import constants, fileio
from ...models import Fulltext
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import FulltextSchema


ns = Namespace(
    "fulltext_uploads",
    path="/fulltexts",
    description="upload or delete fulltext content files",
)


@ns.route("/<int:id>/upload")
@ns.doc(
    summary="upload or delete fulltext content files",
    produces=["application/json"],
)
class FulltextUploadResource(Resource):
    @ns.doc(
        params={
            "review_id": {
                "in": "query",
                "type": "integer",
                "required": False,
                "description": "unique identifier for review whose fulltext upload is to be fetched",
            },
        },
        produces=["application/json"],
        responses={
            200: "successfully got uploaded fulltext content file",
            404: "no fulltext content file with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_INT)
            ),
        },
        location="view_args",
    )
    @use_kwargs(
        {
            "review_id": ma_fields.Int(
                load_default=None, validate=Range(min=1, max=constants.MAX_INT)
            )
        },
        location="query",
    )
    @jwtext.jwt_required()
    def get(self, id, review_id):
        """get fulltext content file for a single fulltext by id"""
        current_user = jwtext.get_current_user()
        filename = None
        if review_id is None:
            for dirname, _, filenames in os.walk(
                current_app.config["FULLTEXT_UPLOADS_DIR"]
            ):
                for ext in current_app.config["ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS"]:
                    fname = f"{id}{ext}"
                    if fname in filenames:
                        filename = fname
                        upload_dir = dirname
                        break
        else:
            # authenticate current user
            from colandr.models import Review

            review = db.session.get(Review, review_id)
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
                    f"{current_user} forbidden to get this review's fulltexts"
                )
            upload_dir = os.path.join(
                current_app.config["FULLTEXT_UPLOADS_DIR"], str(review_id)
            )
            for ext in current_app.config["ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS"]:
                fname = f"{id}{ext}"
                if os.path.isfile(os.path.join(upload_dir, fname)):
                    filename = fname
                    break
        if not filename:
            return not_found_error(f"no uploaded file for <Fulltext(id={id})> found")
        return send_from_directory(upload_dir, filename)

    @ns.doc(
        params={
            "uploaded_file": {
                "in": "formData",
                "type": "file",
                "required": True,
                "description": "full-text content file in a standard format (.pdf or .txt)",
            },
        },
        responses={
            200: "successfully upload full-text file",
            403: "current app user forbidden to upload full-text files for this review",
            404: "no fulltext with matching id was found",
            422: "invalid fulltext upload file type",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            )
        },
        location="view_args",
    )
    @use_kwargs({"uploaded_file": ma_fields.Raw(required=True)}, location="files")
    @jwtext.jwt_required()
    def post(self, id, uploaded_file):
        """upload fulltext content file for a single fulltext by id"""
        current_user = jwtext.get_current_user()
        fulltext = db.session.get(Fulltext, id)
        if not fulltext:
            return not_found_error(f"<Fulltext(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.user_review_assoc.filter_by(
                review_id=fulltext.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to upload fulltext files to this review"
            )
        _, ext = os.path.splitext(uploaded_file.filename)
        if ext not in current_app.config["ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS"]:
            return bad_request_error(f'invalid fulltext upload file type: "{ext}"')
        # assign filename based an id, and full path
        filename = f"{id}{ext}"
        fulltext.filename = filename
        fulltext.original_filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(
            current_app.config["FULLTEXT_UPLOADS_DIR"],
            str(fulltext.review_id),
            filename,
        )
        # HACK: make review directory if doesn't already exist
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        # save file content to disk
        uploaded_file.save(filepath)
        # extract content from disk, depending on type
        if ext == ".txt":
            with io.open(filepath, mode="rb") as f:
                text_content = f.read()
        elif ext == ".pdf":
            # extract_text_script = os.path.join(
            #     current_app.config['COLANDR_APP_DIR'], 'scripts/extractText.sh'
            # )
            # text_content = subprocess.check_output(
            #     [extract_text_script, '--filename', filepath],
            #     stderr=subprocess.STDOUT,
            # )
            text_content = fileio.pdf.read(filepath).encode("utf-8")
        fulltext.text_content = ftfy.fix_text(text_content.decode(errors="ignore"))
        db.session.commit()
        current_app.logger.info(
            'uploaded "%s" for %s', fulltext.original_filename, fulltext
        )

        # parse the fulltext text content and get its word2vec vector
        tasks.get_fulltext_text_content_vector.apply_async(
            args=[id], queue="fast", countdown=3
        )

        return FulltextSchema().dump(fulltext)

    @ns.doc(
        responses={
            204: "successfully deleted fulltext file",
            403: "current app user forbidden to delete fulltext files for this review",
            404: "no fulltext with matching id was found",
            422: "no uploaded content file found for this fulltext",
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
        """delete fulltext content file for a single fulltext by id"""
        current_user = jwtext.get_current_user()
        fulltext = db.session.get(Fulltext, id)
        if not fulltext:
            return not_found_error(f"<Fulltext(id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.user_review_assoc.filter_by(
                review_id=fulltext.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to upload fulltext files to this review"
            )
        filename = fulltext.filename
        if filename is None:
            return bad_request_error(
                "user can't delete a fulltext upload that doesn't exist"
            )
        filepath = os.path.join(
            current_app.config["FULLTEXT_UPLOADS_DIR"],
            str(fulltext.review_id),
            filename,
        )
        try:
            os.remove(filepath)
        except OSError:
            msg = "error removing uploaded full-text file from disk"
            current_app.logger.exception(msg + "\n")
            return not_found_error(msg)
        fulltext.filename = None
        db.session.commit()
        current_app.logger.info('deleted uploaded file "%s "for %s', filename, fulltext)
        return "", 204
