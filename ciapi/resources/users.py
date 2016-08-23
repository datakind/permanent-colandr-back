from flask import jsonify, request
from flask_restful import Resource
from flask_restful_swagger import swagger
from marshmallow import validate
from psycopg2.extensions import AsIs
from webargs import fields
from webargs.flaskparser import use_kwargs  # use_args

from ciapi import PGDB
import cipy


USERS_DDL = cipy.db.db_utils.get_ddl('users')


class User(Resource):

    @swagger.operation()
    @use_kwargs({
        'user_id': fields.Int(
            required=True, location='view_args',
            validate=validate.Range(min=1, max=2147483647)),
        'fields': fields.DelimitedList(
            fields.String(), delimiter=',',
            missing=['user_id', 'name', 'email', 'review_ids', 'owned_review_ids'])
        })
    def get(self, user_id, fields):
        query = """
            SELECT %(fields)s
            FROM users
            WHERE user_id = %(user_id)s
            """
        bindings = {'fields': AsIs(','.join(fields)),
                    'user_id': user_id}
        results = list(PGDB.run_query(query, bindings=bindings))
        if not results:
            raise Exception()
        return jsonify(results[0])


# TODO: password should be encrypted?
class AppUser(Resource):

    @use_kwargs({
        'name': fields.String(
            required=True, validate=validate.Length(min=6, max=200),
            error_messages={'required': '`name` is required!'}),
        'email': fields.Email(
            required=True,
            validate=[validate.Length(min=6, max=200), validate.Email()]),
        'password': fields.String(required=True),
        'test': fields.Boolean(missing=False)
        })
    def post(self, name, email, password, test):
        user = {'name': name, 'email': email, 'password': password}
        user = cipy.validation.user.User(user)
        user.validate()
        valid_user = user.to_primitive()
        if test is True:
            _ = list(PGDB.run_query(
                USERS_DDL['templates']['create_user'],
                bindings=valid_user,
                act=False))
            return valid_user
        else:
            created_user_id = list(PGDB.run_query(
                USERS_DDL['templates']['create_user'],
                bindings=valid_user,
                act=True))[0]['user_id']
            return created_user_id
