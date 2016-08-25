from psycopg2.extensions import AsIs
from psycopg2 import IntegrityError as DataIntegrityError

from flask import jsonify, request
from flask_restful import Resource, abort
from flask_restful_swagger import swagger

from marshmallow import Schema, fields, ValidationError
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
        required=True, load_only=True)
    review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        required=True, allow_none=True)
    owned_review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        required=True, allow_none=True)

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
            #raise cipy.exceptions.MissingDataException()
            abort(404, message='User not found with id="{}"'.format(user_id))
        return UserSchema().dump(results[0]).data

    @swagger.operation()
    @use_kwargs({
        'name': fields.String(
            required=True, validate=Length(min=1, max=200)),
        'email': fields.Email(
            required=True, validate=[Email(), Length(max=200)]),
        'password': fields.String(
            required=True),
        'review_ids': fields.List(
            fields.Int(validate=Range(min=1, max=2147483647)),
            required=True, missing=None, allow_none=True),
        'owned_review_ids': fields.List(
            fields.Int(validate=Range(min=1, max=2147483647)),
            required=True, missing=None, allow_none=True),
        'test': fields.Boolean(missing=False)
        })
    def post(self, name, email, password, review_ids, owned_review_ids, test):
        data = {'name': name, 'email': email, 'password': password,
                'review_ids': review_ids, 'owned_review_ids': owned_review_ids}
        try:
            UserSchema().validate(data)
        except ValidationError:
            raise

        if test is True:
            list(PGDB.run_query(
                USERS_DDL['templates']['create_user'],
                bindings=data,
                act=False))
            return data
        else:
            try:
                created_user_id = list(PGDB.run_query(
                    USERS_DDL['templates']['create_user'],
                    bindings=data,
                    act=True))[0]['user_id']
                return created_user_id
            except DataIntegrityError:
                raise

    @swagger.operation()
    @use_kwargs({
        'user_id': fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        })
    def delete(self, user_id):
        return user_id
