from flask import jsonify, request, session
from flask_restful import Resource
from marshmallow import validate
from psycopg2.extensions import AsIs
from webargs import fields
from webargs.flaskparser import use_kwargs  # use_args

from ciapi import PGDB


class Review(Resource):

    @use_kwargs({
        'review_id': fields.Int(
            required=True, location='view_args',
            validate=validate.Range(min=1, max=2147483647)),
        'fields': fields.DelimitedList(
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


class Reviews(Resource):

    @use_kwargs({
        'fields': fields.DelimitedList(
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
