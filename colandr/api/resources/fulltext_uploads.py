import io
import os
import subprocess

from flask import current_app, g
from flask_restful import Resource
from flask_restful_swagger import swagger
from werkzeug.utils import secure_filename

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from textacy.preprocess import fix_bad_unicode

from ...lib import constants, utils
from ...models import db, Fulltext
from ..errors import no_data_found, unauthorized, validation
from ..schemas import FulltextSchema
from ..authentication import auth


logger = utils.get_console_logger(__name__)


class FulltextUploadResource(Resource):

    method_decorators = [auth.login_required]

    # NOTE: the get method for this resource is actually in the app's __init__.py
    # it required using flask-style routes instead of flask-restful

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, id, uploaded_file, test):
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to upload fulltext files to this review'.format(
                    g.current_user))
        _, ext = os.path.splitext(uploaded_file.filename)
        if ext not in current_app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
            return validation('invalid fulltext upload file type: "{}"'.format(ext))
        # assign filename based an id, and full path
        filename = '{}{}'.format(id, ext)
        fulltext.filename = filename
        fulltext.original_filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(
            current_app.config['FULLTEXT_UPLOAD_FOLDER'], filename)
        if test is False:
            # save file content to disk
            uploaded_file.save(filepath)
            # extract content from disk, depending on type
            if ext == '.txt':
                with io.open(filepath, mode='rb') as f:
                    text_content = f.read()
            elif ext == '.pdf':
                extract_text_script = os.path.join(
                    current_app.config['COLANDR_APP_DIR'],
                    'pdfestrian/bin/extractText.sh')
                text_content = subprocess.check_output(
                    [extract_text_script, '--filename', filepath],
                    stderr=subprocess.STDOUT)
            fulltext.text_content = fix_bad_unicode(
                text_content.decode(errors='ignore'))
            db.session.commit()
            logger.info(
                'uploaded "%s" for %s', fulltext.original_filename, fulltext)
        return FulltextSchema().dump(fulltext).data

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to upload fulltext files to this review'.format(
                    g.current_user))
        if fulltext.filename is None:
            return validation("user can't delete a fulltext upload that doesn't exist")
        if test is False:
            filepath = os.path.join(
                current_app.config['FULLTEXT_UPLOAD_FOLDER'], fulltext.filename)
            os.remove(filepath)
            fulltext.filename = None
            db.session.commit()
            logger.info('deleted uploaded file for %s', fulltext)
