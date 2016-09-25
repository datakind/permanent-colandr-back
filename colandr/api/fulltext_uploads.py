import os

from flask import current_app, g, send_from_directory
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ..lib import constants
from ..models import db, Fulltext
from .errors import no_data_found, unauthorized, validation
from .schemas import FulltextSchema
from .authentication import auth


class FulltextUploadResource(Resource):

    method_decorators = [auth.login_required]

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
        filename = '{}{}'.format(id, ext)
        fulltext.filename = filename
        if test is False:
            db.session.commit()
            uploaded_file.save(
                os.path.join(current_app.config['FULLTEXT_UPLOAD_FOLDER'], filename))
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
