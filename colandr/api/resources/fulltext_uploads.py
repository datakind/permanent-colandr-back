import io
import os
import subprocess

import ftfy
from flask import current_app, g
from flask_restx import Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs
from werkzeug.utils import secure_filename

from colandr import api_

from ...lib import constants
from ...models import Fulltext, db
from ...tasks import get_fulltext_text_content_vector
from ..authentication import auth
from ..errors import forbidden_error, not_found_error, validation_error
from ..schemas import FulltextSchema


ns = api_.namespace(
    'fulltext_uploads', path='/fulltexts',
    description='upload or delete fulltext content files')


@ns.route('/<int:id>/upload')
@ns.doc(
    summary='upload or delete fulltext content files',
    produces=['application/json'],
    )
class FulltextUploadResource(Resource):

    method_decorators = [auth.login_required]

    # NOTE: the get method for this resource is actually in the app's __init__.py
    # it required using flask-style routes instead of flask-restful

    @ns.doc(
        params={
            'uploaded_file': {'in': 'formData', 'type': 'file', 'required': True,
                              'description': 'full-text content file in a standard format (.pdf or .txt)'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'successfully upload full-text file',
            403: 'current app user forbidden to upload full-text files for this review',
            404: 'no fulltext with matching id was found',
            422: 'invalid fulltext upload file type',
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, id, uploaded_file, test):
        """upload fulltext content file for a single fulltext by id"""
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return not_found_error('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return forbidden_error(
                '{} forbidden to upload fulltext files to this review'.format(
                    g.current_user))
        _, ext = os.path.splitext(uploaded_file.filename)
        if ext not in current_app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
            return validation_error('invalid fulltext upload file type: "{}"'.format(ext))
        # assign filename based an id, and full path
        filename = '{}{}'.format(id, ext)
        fulltext.filename = filename
        fulltext.original_filename = secure_filename(uploaded_file.filename)
        filepath = os.path.join(
            current_app.config['FULLTEXT_UPLOADS_DIR'],
            str(fulltext.review_id),
            filename)
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
            fulltext.text_content = ftfy.fix_text(
                text_content.decode(errors='ignore'))
            db.session.commit()
            current_app.logger.info(
                'uploaded "%s" for %s', fulltext.original_filename, fulltext)

            # parse the fulltext text content and get its word2vec vector
            get_fulltext_text_content_vector.apply_async(
                args=[fulltext.review_id, id], countdown=5)

        return FulltextSchema().dump(fulltext).data

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'request was valid, but record not deleted because `test=False`',
            204: 'successfully deleted fulltext file',
            403: 'current app user forbidden to delete fulltext files for this review',
            404: 'no fulltext with matching id was found',
            422: 'no uploaded content file found for this fulltext',
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        """delete fulltext content file for a single fulltext by id"""
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return not_found_error('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return forbidden_error(
                '{} forbidden to upload fulltext files to this review'.format(
                    g.current_user))
        filename = fulltext.filename
        if filename is None:
            return validation_error("user can't delete a fulltext upload that doesn't exist")
        if test is False:
            filepath = os.path.join(
                current_app.config['FULLTEXT_UPLOADS_DIR'],
                str(fulltext.review_id),
                filename)
            try:
                os.remove(filepath)
            except OSError as e:
                msg = 'error removing uploaded full-text file from disk'
                current_app.logger.exception(msg + '\n')
                return not_found_error(msg)
            fulltext.filename = None
            db.session.commit()
            current_app.logger.info(
                'deleted uploaded file "%s "for %s', filename, fulltext)
            return '', 204
        else:
            return '', 200
