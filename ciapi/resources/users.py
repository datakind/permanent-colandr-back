from psycopg2.extensions import AsIs

from flask import jsonify, request
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import Schema, fields
from marshmallow.validate import Email, Length, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs  # use_args

from ciapi import PGDB
import cipy


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
        required=True)
    review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        required=True)
    owned_review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        required=True)

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
        bindings = {'fields': '*' if fields == ['all'] else AsIs(','.join(fields)),
                    'user_id': user_id}
        results = list(PGDB.run_query(query, bindings=bindings))
        if not results:
            raise Exception()
        return jsonify(results[0])

    @swagger.operation()
    @use_kwargs({
        'name': fields.String(
            required=True, validate=Length(min=1, max=200)),
        'email': fields.Email(
            required=True, validate=[Email(), Length(max=200)]),
        'password': fields.String(required=True),
        'test': fields.Boolean(missing=False)
        })
    def post(self, name, email, password, test):
        # user = {'name': name, 'email': email, 'password': password}
        # user = cipy.validation.user.User(user)
        # user.validate()
        # valid_user = user.to_primitive()
        user = UserSchema().load({'name': name, 'email': email, 'password': password})
        return user
        # if test is True:
        #     _ = list(PGDB.run_query(
        #         USERS_DDL['templates']['create_user'],
        #         bindings=valid_user,
        #         act=False))
        #     return valid_user
        # else:
        #     created_user_id = list(PGDB.run_query(
        #         USERS_DDL['templates']['create_user'],
        #         bindings=valid_user,
        #         act=True))[0]['user_id']
        #     return created_user_id
