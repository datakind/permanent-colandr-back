from flask import g, current_app
from flask_restx import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from colandr import api_
from ...lib import constants
from ...models import db, Fulltext
from ..errors import not_found_error, forbidden_error
from ..schemas import FulltextSchema
from ..authentication import auth


ns = api_.namespace(
    'fulltexts', path='/fulltexts',
    description='get and delete fulltexts')


@ns.route('/<int:id>')
@ns.doc(
    summary='get and delete fulltexts',
    produces=['application/json'],
    )
class FulltextResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        params={'fields': {'in': 'query', 'type': 'string',
                           'description': 'comma-delimited list-as-string of fulltext fields to return'},
                },
        responses={
            200: 'successfully got fulltext record',
            403: 'current app user forbidden to get fulltext record',
            404: 'no fulltext with matching id was found',
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
        """get record for a single fulltext by id"""
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return not_found_error('<Fulltext(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                fulltext.review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return forbidden_error(
                '{} forbidden to get this fulltext'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        current_app.logger.debug('got %s', fulltext)
        return FulltextSchema(only=fields).dump(fulltext).data

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'request was valid, but record not deleted because `test=False`',
            204: 'successfully deleted fulltext record',
            403: 'current app user forbidden to delete fulltext record',
            404: 'no fulltext with matching id was found'
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        """delete record for a single fulltext by id"""
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return not_found_error('<Fulltext(id={})> not found'.format(id))
        if fulltext.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return forbidden_error(
                '{} forbidden to delete this fulltext'.format(g.current_user))
        db.session.delete(fulltext)
        if test is False:
            db.session.commit()
            current_app.logger.info('deleted %s', fulltext)
            return '', 204
        else:
            db.session.rollback()
            return '', 200
