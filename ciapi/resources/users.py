import flask
from flask_restful import Resource  # , abort
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Email, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ciapi.models import db, User, Review
from ciapi.schemas import UserSchema
from ciapi.auth import auth


class UserResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'user_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, user_id, fields):
        user = db.session.query(User).get(user_id)
        if not user:
            raise NoResultFound
        elif user.id != flask.session['user']['id']:
            raise Exception('{} not authorized to get this user'.format(user))
        return UserSchema(only=fields).dump(user).data

    @swagger.operation()
    @use_kwargs({
        'user_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, user_id, test):
        user = db.session.query(User).get(user_id)
        if not user:
            raise NoResultFound
        elif user.id != flask.session['user']['id']:
            raise Exception('{} not authorized to delete this user'.format(user))
        if test is False:
            db.session.delete(user)
            db.session.commit()

    @swagger.operation()
    @use_args(UserSchema(partial=True))
    @use_kwargs({
        'user_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, user_id, test):
        user = db.session.query(User).get(user_id)
        if not user:
            raise NoResultFound
        elif user.id != flask.session['user']['id']:
            raise Exception('{} not authorized to update this user'.format(user))
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
    @swagger.operation()
    @use_kwargs({
        'email': ma_fields.Email(
            missing=None, validate=Email()),
        'review_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=2147483647))
        })
    def get(self, email, review_id):
        if email:
            user = db.session.query(User).filter_by(email=email).one_or_none()
            if not user:
                return NoResultFound
            else:
                return UserSchema().dump(user).data
        elif review_id:
            review = db.session.query(Review).get(review_id)
            if not review:
                raise NoResultFound
            users = review.users
            return UserSchema(many=True).dump(users).data

    @swagger.operation()
    @use_args(UserSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        user = User(**args)
        if test is False:
            db.session.add(user)
            db.session.commit()
        return UserSchema().dump(user).data
