# import logging

# from psycopg2.extensions import AsIs
# from psycopg2 import IntegrityError as DataIntegrityError

# from flask import jsonify, request, session
from flask_restful import Resource  # , abort
from flask_restful_swagger import swagger
from sqlalchemy.orm import load_only
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields
from marshmallow.validate import Email, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ciapi.models import db, User, Review
from ciapi.schemas import UserSchema


class UserResource(Resource):

    @swagger.operation()
    @use_kwargs({
        'user_id': fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            fields.String(), delimiter=',', missing=None)
        })
    def get(self, user_id, fields):
        if fields is None:
            user = db.session.query(User).get(user_id)
            if not user:
                raise NoResultFound
        else:
            user = db.session.query(User)\
                     .filter_by(id=user_id)\
                     .options(load_only(*fields))\
                     .one()
        return UserSchema().dump(user).data

    @swagger.operation()
    @use_kwargs({
        'user_id': fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': fields.Boolean(missing=False)
        })
    def delete(self, user_id, test):
        # TODO
        # if user_id != session['user']['user_id']:
        #     # UnauthorizedException
        #     raise Exception('user not authorized to delete this user')
        user = db.session.query(User).get(user_id)
        if not user:
            raise NoResultFound
        if test is False:
            db.session.delete(user)
            db.session.commit()

#     @swagger.operation()
#     @use_args(UserSchema())
#     @use_kwargs({'test': fields.Boolean(missing=False)})
#     def post(self, args, test):
#         if test is True:
#             list(PGDB.run_query(
#                 USERS_DDL['templates']['create_user'],
#                 bindings=args,
#                 act=False))
#             return args
#         else:
#             try:
#                 created_user_id = list(PGDB.run_query(
#                     USERS_DDL['templates']['create_user'],
#                     bindings=args,
#                     act=True))[0]['user_id']
#                 return created_user_id
#             except DataIntegrityError:
#                 raise


class UsersResource(Resource):

    @swagger.operation()
    @use_kwargs({
        'email': fields.Email(
            missing=None, validate=Email()),
        'review_id': fields.Int(
            missing=None, validate=Range(min=1, max=2147483647))
        })
    def get(self, email, review_id):
        if email:
            user = db.session.query(User).filter_by(email=email).one()
            return UserSchema().dump(user).data
        elif review_id:
            review = db.session.query(Review).get(review_id)
            if not review:
                raise NoResultFound
            users = review.users
            return UserSchema(many=True).dump(users).data

    @swagger.operation()
    @use_args(UserSchema())
    @use_kwargs({'test': fields.Boolean(missing=False)})
    def post(self, args, test):
        user = User(**args)
        if test is False:
            db.session.add(user)
            db.session.commit()
        return UserSchema().dump(user).data
