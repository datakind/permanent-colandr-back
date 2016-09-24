import os

from flask import current_app, g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.flaskparser import use_kwargs

from ..lib import constants
from ..models import db, Citation, Fulltext
from .errors import forbidden, no_data_found, unauthorized, validation
from .schemas import FulltextSchema
from .authentication import auth


class FulltextsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'citation_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, citation_id, test):
        citation = db.session.query(Citation).get(citation_id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(citation_id))
        review_id = citation.review_id
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add fulltexts to this review'.format(g.current_user))
        if citation.status != 'included':
            return forbidden(
                '{} status is not "included", so fulltext can not be uploaded'.format(
                    citation))
        _, ext = os.path.splitext(uploaded_file.filename)
        if ext not in current_app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
            return validation('invalid fulltext upload file type: "{}"'.format(ext))
        filename = '{}{}'.format(citation_id, ext)
        fulltext = Fulltext(review_id, citation_id, filename, content=None)
        if test is False:
            db.session.add(fulltext)
            uploaded_file.save(
                os.path.join(current_app.config['FULLTEXT_UPLOAD_FOLDER'], filename))
            db.session.commit()
        return FulltextSchema().dump(fulltext).data
