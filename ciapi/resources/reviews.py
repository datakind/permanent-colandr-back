import arrow
from flask import jsonify, request, session
from flask_restful import Resource
from flask_restful_swagger import swagger
from marshmallow import Schema, fields
from marshmallow.validate import Length, Range
from psycopg2.extensions import AsIs
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs  # use_args

from ciapi import PGDB


class ReviewSettingsSchema(Schema):
    num_citation_screening_reviewers = fields.Int(
        required=True, missing=2, validate=Range(min=1, max=3))
    num_fulltext_screening_reviewers = fields.Int(
        required=True, missing=2, validate=Range(min=1, max=3))
    required_citation_screener_id = fields.Int(
        validate=Range(min=0, max=2147483647))
    required_fulltext_screener_id = fields.Int(
        validate=Range(min=0, max=2147483647))

    class Meta:
        strict = True


class ReviewSchema(Schema):
    review_id = fields.Int(
        dump_only=True)
    created_ts = fields.DateTime(
        format='iso', missing=arrow.utcnow().datetime, dump_only=True)
    owner_user_id = fields.Int(
        required=True, validate=Range(min=1, max=2147483647))
    user_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        required=True)
    name = fields.Str(
        required=True, validate=Length(max=500))
    description = fields.Str()
    settings = fields.Nested(
        ReviewSettingsSchema,
        required=True, missing=ReviewSettingsSchema().load({}).data)

    class Meta:
        strict = True


class Review(Resource):

    @swagger.operation()
    @use_kwargs({
        'review_id': fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            fields.String(), delimiter=',',
            missing=['review_id', 'created_ts', 'owner_user_id', 'user_ids', 'name', 'description'])
        })
    def get(self, review_id, fields):
        if review_id not in session['user']['review_ids']:
            raise Exception('user not authorized to see this review')
        query = """
            SELECT %(fields)s
            FROM reviews
            WHERE review_id = %(review_id)s
            """
        bindings = {'fields': AsIs(','.join(fields)),
                    'review_id': review_id}
        result = list(PGDB.run_query(query, bindings=bindings))
        if not result:
            raise Exception('no results found')
        return jsonify(result[0])

    @swagger.operation()
    @use_kwargs(ReviewSchema())
    def post(self, owner_user_id, user_ids, name, description):
        return


class Reviews(Resource):

    @swagger.operation()
    @use_kwargs({
        'fields': DelimitedList(
            fields.String(), delimiter=',',
            missing=['review_id', 'created_ts', 'owner_user_id', 'user_ids', 'name'])
        })
    def get(self, fields):
        query = """
            SELECT %(fields)s
            FROM reviews
            WHERE %(user_id)s = ANY(user_ids)
            """
        bindings = {'fields': AsIs(','.join(fields)),
                    'user_id': session['user']['user_id']}
        result = list(PGDB.run_query(query, bindings=bindings))
        if not result:
            raise Exception('no results found')
        return jsonify(result)
