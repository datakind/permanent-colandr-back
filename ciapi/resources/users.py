import logging

from psycopg2.extensions import AsIs
from psycopg2 import IntegrityError as DataIntegrityError

from flask import jsonify, request, session
from flask_restful import Resource, abort
from flask_restful_swagger import swagger

from marshmallow import Schema, fields, ValidationError
from marshmallow.validate import Email, Length, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ciapi import PGDB
import cipy


REVIEWS_DDL = cipy.db.db_utils.get_ddl('reviews')
USERS_DDL = cipy.db.db_utils.get_ddl('users')


class UserSchema(Schema):
    user_id = fields.Int(
        dump_only=True, validate=Range(min=1, max=2147483647))
    created_ts = fields.DateTime(
        dump_only=True, format='iso')
    name = fields.Str(
        required=True, validate=Length(min=1, max=200))
    email = fields.Email(
        required=True, validate=[Email(), Length(max=200)])
    password = fields.Str(
        required=True, load_only=True)
    review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        missing=None)
    owned_review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        missing=None)

    class Meta:
        strict = True


class User(Resource):

    @swagger.operation()
    @use_kwargs({
        'user_id': fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            fields.String(), delimiter=',', missing=['all'])
        })
    def get(self, user_id, fields):
        query = """
            SELECT %(fields)s
            FROM users
            WHERE user_id = %(user_id)s
            """
        bindings = {
            'fields': AsIs('*') if fields == ['all'] else AsIs(','.join(fields)),
            'user_id': user_id}
        results = list(PGDB.run_query(query, bindings=bindings))
        if not results:
            # MissingDataException
            raise Exception('User not found with id="{}"'.format(user_id))
        return UserSchema().dump(results[0]).data

    @swagger.operation()
    @use_args(UserSchema())
    @use_kwargs({'test': fields.Boolean(missing=False)})
    def post(self, args, test):
        if test is True:
            list(PGDB.run_query(
                USERS_DDL['templates']['create_user'],
                bindings=args,
                act=False))
            return args
        else:
            try:
                created_user_id = list(PGDB.run_query(
                    USERS_DDL['templates']['create_user'],
                    bindings=args,
                    act=True))[0]['user_id']
                return created_user_id
            except DataIntegrityError:
                raise

    @swagger.operation()
    @use_kwargs({
        'user_id': fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': fields.Boolean(missing=False)
        })
    def delete(self, user_id, test):
        if user_id != session['user']['user_id']:
            # UnauthorizedException
            raise Exception('user not authorized to delete this user')
        act = not test
        updated_reviews = PGDB.run_query(
            REVIEWS_DDL['templates']['remove_deleted_user'],
            bindings={'user_id': user_id},
            act=act)
        PGDB.execute(
            USERS_DDL['templates']['delete_user'],
            bindings={'user_id': user_id},
            act=act)
        if test is False:
            updated_review_ids = [review['review_id'] for review in updated_reviews]
            logging.info('user id=%s removed from review ids=%s',
                         user_id, updated_review_ids)
        else:
            logging.info('deleted user id=%s from reviews (TEST)', user_id)
