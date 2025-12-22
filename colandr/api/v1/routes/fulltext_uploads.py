import io
import os

import apiflask as af
import flask_jwt_extended as jwtext
import ftfy
from flask import current_app, send_file
from flask.views import MethodView
from werkzeug.utils import secure_filename

from .... import models, tasks
from ....extensions import db
from ....lib import fileio
from .. import errors, schemas


# TODO: "fulltext upload" is a weird name, and inconsistent with "citations import"
# in a v2 API, naming / routing should be made more consistent and sensible
bp = af.APIBlueprint("fulltext_uploads", __name__, url_prefix="/fulltexts")


class FulltextUploadAPI(MethodView):
    @bp.doc(
        summary="get file for a single fulltext",
        responses={
            200: "successfully got uploaded fulltext content file",
            404: "no fulltext content file with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "review_id": af.fields.Integer(
                required=True,
                validate=af.validators.Range(min=1),
                metadata={
                    "description": "unique identifier for review whose fulltext upload is to be fetched"
                },
            )
        },
        location="query",
    )
    @bp.output(
        af.schemas.FileSchema(type="string", format="binary"),
        content_type="application/pdf",
    )
    @jwtext.jwt_required()
    def get(self, id, query_data):
        review_id = query_data["review_id"]
        current_user = jwtext.get_current_user()
        fs = current_app.extensions["filesystem"]

        filepath = None
        # TODO: if we need review_id to be optional, reenable this block
        # if review_id is None:
        #     allowed_exts = current_app.config["ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS"]
        #     for fpath in fs.glob(
        #         os.path.join(current_app.config["FULLTEXT_UPLOADS_DIR"], "**"),
        #         maxdepth=2,
        #     ):
        #         fname = os.path.basename(fpath)
        #         # directories will have stem == "", so don't satisfy if condition
        #         stem, ext = os.path.splitext(fname)
        #         if stem == str(id) and ext in allowed_exts:
        #             filepath = fpath
        #             break
        # else:
        # authenticate current user
        review = db.session.get(models.Review, review_id)
        if not review:
            raise errors.NotFoundError(message=f"<Review(id={review_id})> not found")

        if (
            current_user.is_admin is False
            and review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get this review's fulltexts"
            )

        upload_dir = os.path.join(
            current_app.config["FULLTEXT_UPLOADS_DIR"], str(review_id)
        )
        for ext in current_app.config["ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS"]:
            fpath = os.path.join(upload_dir, f"{id}{ext}")
            if fs.exists(fpath):
                filepath = fpath
                break
        if not filepath:
            raise errors.NotFoundError(
                message=f"no uploaded file for <Study(id={id})> found"
            )

        # read file contents into memory as bytes, then wrap up in a file-like interface
        # which flask's send_file can then pretend is a file on disk
        with fs.open(filepath, mode="rb") as f:
            file_contents = f.read()
        return send_file(
            io.BytesIO(file_contents),
            mimetype="application/pdf",
            as_attachment=False,
            download_name=os.path.basename(filepath),
        )

    @bp.doc(
        summary="upload file for a single fulltext",
        responses={
            200: "successfully upload full-text file",
            403: "current app user forbidden to upload full-text files for this review",
            404: "no fulltext with matching id was found",
            422: "invalid fulltext upload file type",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "uploaded_file": af.fields.File(
                required=True,
                metadata={
                    "description": "full-text content file in a standard format (.pdf or .txt)"
                },
            )
        },
        location="files",
    )
    @bp.output(schemas.FulltextSchema)
    @jwtext.jwt_required()
    def post(self, id, files_data):
        uploaded_file = files_data["uploaded_file"]
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
        ) or study.review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to upload fulltext files to this review"
            )

        _, ext = os.path.splitext(uploaded_file.filename)
        if ext not in current_app.config["ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS"]:
            raise errors.BadRequestError(
                message=f'invalid fulltext upload file type: "{ext}"'
            )

        # assign filename based an id, and full path
        filename = f"{id}{ext}"
        filepath = os.path.join(
            current_app.config["FULLTEXT_UPLOADS_DIR"],
            str(study.review_id),
            filename,
        )
        fs = current_app.extensions["filesystem"]
        # make review directory if doesn't already exist
        fs.makedirs(os.path.dirname(filepath), exist_ok=True)
        # save content to file on filesystem
        text_content = uploaded_file.stream.read()
        with fs.open(filepath, mode="wb") as f:
            # uploaded_file.save(f) may also work well
            f.write(text_content)

        # actually parse raw bytes in case of proper pdf file
        if ext == ".pdf":
            text_content = fileio.pdf.read(stream=io.BytesIO(text_content)).encode(
                "utf-8"
            )

        fulltext = {
            "filename": filename,
            "original_filename": secure_filename(uploaded_file.filename),
            "text_content": ftfy.fix_text(text_content.decode(errors="ignore")),
        }
        study.fulltext = fulltext
        db.session.commit()

        current_app.logger.info(
            'uploaded "%s" for %s to "%s"',
            fulltext["original_filename"],
            study,
            filepath,
        )

        # parse the fulltext text content and get its word2vec vector
        # TODO: figure out why queue="fast" doesn't work here
        tasks.get_fulltext_text_content_vector.apply_async(args=[id], countdown=3)

        fulltext = _make_pseudo_fulltext_record(study)
        return fulltext

    @bp.doc(
        summary="delete file for a single fulltext",
        responses={
            204: "successfully deleted fulltext file",
            403: "current app user forbidden to delete fulltext files for this review",
            404: "no fulltext with matching id was found",
            422: "no uploaded content file found for this fulltext",
        },
        security="TokenAuth",
    )
    @bp.output({}, 204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id):
        """delete fulltext content file for a single fulltext by id"""
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
                message=f"{current_user} forbidden to upload fulltext files to this review"
            )

        fulltext = study.fulltext
        if not fulltext:
            raise errors.BadRequestError(
                message="user can't delete a fulltext upload that doesn't exist"
            )

        filepath = os.path.join(
            current_app.config["FULLTEXT_UPLOADS_DIR"],
            str(study.review_id),
            fulltext["filename"],
        )
        fs = current_app.extensions["filesystem"]
        try:
            fs.rm_file(filepath)
        except IOError:
            msg = "error removing uploaded full-text file from disk"
            current_app.logger.exception(msg + "\n")
            raise errors.NotFoundError(message=msg)
        study.fulltext = {}
        db.session.commit()
        current_app.logger.info(
            "%s deleted uploaded file '%s' for %s",
            current_user,
            fulltext["filename"],
            study,
        )
        return ""


def _make_pseudo_fulltext_record(study: models.Study) -> dict:
    # NOTE: this is an exact duplicate of function in fulltexts.py
    # pretend that fulltexts are still separate records for api consistency
    fulltext = study.fulltext
    if fulltext:
        fulltext |= {
            "id": study.id,
            "review_id": study.review_id,
            "created_at": study.created_at,
            "updated_at": study.updated_at,
        }
    return fulltext


bp.add_url_rule(
    "/<int:id>/upload", view_func=FulltextUploadAPI.as_view("fulltext_upload")
)
