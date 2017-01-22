from flask import g
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Email, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, utils
from ...models import db, User, Review
from ..errors import no_data_found, unauthorized
from ..swagger import user_model
from ..schemas import UserSchema
from ..authentication import auth
from colandr import api_

logger = utils.get_console_logger(__name__)
ns = api_.namespace(
    'users', path='/users',
    description='get, create, delete, update users')


@ns.route('/<int:id>')
@ns.doc(
    summary='get, delete, and modify data for single users',
    produces=['application/json'],
    )
class UserResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        params={'fields': {'in': 'query', 'type': 'string',
                           'description': 'comma-delimited list-as-string of user fields to return'},
                },
        responses={200: 'successfully got user record',
                   401: 'current app user not authorized to get user record',
                   404: 'no user with matching id was found',
                   }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
        """get record for a single user by id"""
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

    @ns.doc(
        params={'test': {'in': 'query', 'type': 'boolean', 'default': False,
                         'description': 'if True, request will be validated but no data will be affected'},
                },
        responses={204: 'successfully deleted user record',
                   401: 'current app user not authorized to delete user record',
                   404: 'no user with matching id was found',
                   }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        """delete record for a single user by id"""
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

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        body=(user_model, 'user data to be modified'),
        responses={
            200: 'user data was modified (if test = False)',
            401: 'current app user not authorized to modify user',
            404: 'no user with matching id was found',
            }
        )
    @use_args(UserSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        """modify record for a single user by id"""
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


@ns.route('/')
@ns.doc(
    summary='get existing and create new users',
    produces=['application/json'],
    )
class UsersResource(Resource):

    @auth.login_required
    @ns.doc(
        params={'email': {'in': 'query', 'type': 'string',
                          'description': 'email address of user'},
                'review_id': {'in': 'query', 'type': 'integer',
                              'description': 'unique review id on which users are collaborators'},
                },
        responses={200: 'successfully got user record(s)',
                   401: 'current app user not authorized to get user record(s)',
                   404: 'no matching user(s) found',
                   }
        )
    @use_kwargs({
        'email': ma_fields.Email(
            missing=None, validate=Email()),
        'review_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT))
        })
    def get(self, email, review_id):
        """get user record(s) for one or more matching users"""
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

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        body=(user_model, 'user data to be created'),
        responses={
            200: 'user was created (or would have been created if test had been False)',
            401: 'current app user not authorized to create user',
            }
        )
    @use_args(UserSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        """create new user (ADMIN ONLY)"""
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
