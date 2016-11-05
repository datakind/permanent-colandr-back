from flask import g
from flask_restful import Resource
# from flask_restful_swagger import swagger
from flask_restful_swagger_2 import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Email, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, utils
from ...models import db, User, Review
from ..errors import no_data_found, unauthorized
from ..schemas import UserSchema
from ..authentication import auth


logger = utils.get_console_logger(__name__)


class UserResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.doc({
        'tags': ['users'],
        'description': 'get a single user by id',
        'produces': ['application/json'],
        'parameters': [
            {'name': 'id', 'in': 'path', 'type': 'integer', 'required': True,
             'description': 'unique identifier for user'},
            {'name': 'fields', 'in': 'query', 'type': 'string',
             'description': 'comma-delimited list-as-string of user fields to return'},
            ],
        'responses': {
            '200': {'description': 'successfuly got user'},
            '401': {'description': 'current app user not authorized to get user'},
            '404': {'description': 'no user with matching id was found'},
            }
        })
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
        if (g.current_user.is_admin is False and id != g.current_user.id and
                any(review.users.filter_by(id=id).one_or_none()
                    for review in g.current_user.reviews) is False):
            return unauthorized(
                '{} not authorized to get this user'.format(g.current_user))
        user = db.session.query(User).get(id)
        if not user:
            return no_data_found('<User(id={})> not found'.format(id))
        if fields and 'id' not in fields:
            fields.append('id')
        return UserSchema(only=fields).dump(user).data

    @swagger.doc({
        'tags': ['users'],
        'description': 'delete a single user by id',
        'produces': ['application/json'],
        'parameters': [
            {'name': 'id', 'in': 'path', 'type': 'integer', 'required': True,
             'description': 'unique identifier for user'},
            {'name': 'test', 'in': 'query', 'type': 'boolean',
             'description': 'if True, no changes to the database are made; if False (default), the db is changed'},
            ],
        'responses': {
            '200': {'description': 'user would have been deleted, if test had been False'},
            '204': {'description': 'successfuly deleted user'},
            '401': {'description': 'current app user not authorized to delete user'},
            '404': {'description': 'no user with matching id was found'}
            }
        })
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        if id != g.current_user.id:
            return unauthorized(
                '{} not authorized to delete this user'.format(g.current_user))
        user = db.session.query(User).get(id)
        if not user:
            return no_data_found('<User(id={})> not found'.format(id))
        db.session.delete(user)
        if test is False:
            db.session.commit()
            logger.info('deleted %s', user)
            return '', 204
        else:
            db.session.rollback()

    @swagger.doc({
        'tags': ['users'],
        'description': 'modify a single user by id',
        'produces': ['application/json'],
        'parameters': [
            {'name': 'id', 'in': 'path', 'type': 'integer', 'required': True,
             'description': 'unique identifier for user'},
            {'name': 'args', 'in': 'body', 'schema': '', 'required': True,
             'description': 'field: value pairs to be updated for user'},
            {'name': 'test', 'in': 'query', 'type': 'boolean',
             'description': 'if True, no changes to the database are made; if False (default), the db is changed'},
            ],
        'responses': {
            '200': {'description': 'user would have been modified, if test had been False'},
            '401': {'description': 'current app user not authorized to modify user'},
            '404': {'description': 'no user with matching id was found'}
            }
        })
    @use_args(UserSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        if id != g.current_user.id:
            return unauthorized(
                '{} not authorized to update this user'.format(g.current_user))
        user = db.session.query(User).get(id)
        if not user:
            return no_data_found('<User(id={})> not found'.format(id))
        for key, value in args.items():
            if key is missing:
                continue
            elif key == 'password':
                setattr(user, key, User.hash_password(value))
            else:
                setattr(user, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return UserSchema().dump(user).data


class UsersResource(Resource):

    @auth.login_required
    @use_kwargs({
        'email': ma_fields.Email(
            missing=None, validate=Email()),
        'review_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT))
        })
    def get(self, email, review_id):
        if email:
            user = db.session.query(User).filter_by(email=email).one_or_none()
            if not user:
                return no_data_found('no user found with email "{}"'.format(email))
            else:
                return UserSchema().dump(user).data
        elif review_id:
            review = db.session.query(Review).get(review_id)
            if not review:
                return no_data_found('<Review(id={})> not found'.format(review_id))
            if (g.current_user.is_admin is False and
                    review.users.filter_by(id=g.current_user.id).one_or_none() is None):
                return unauthorized(
                    '{} not authorized to see users for this review'.format(
                        g.current_user))
            return UserSchema(many=True).dump(review.users).data

    @use_args(UserSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        # TODO: enable this
        # if g.current_user.is_admin is False:
        #     return unauthorized('only admins can add users without confirmation')
        user = User(**args)
        user.is_confirmed = True
        db.session.add(user)
        if test is False:
            db.session.commit()
            logger.info('inserted %s', user)
        else:
            db.session.rollback()
        return UserSchema().dump(user).data
