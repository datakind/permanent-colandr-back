from flask import jsonify, request
from flask_restful import Resource
from marshmallow import validate
from psycopg2.extensions import AsIs
from webargs import fields
from webargs.flaskparser import use_kwargs  # use_args

from ciapi import PGDB


class Citation(Resource):

    @use_kwargs({
        'citation_id': fields.Int(
            required=True, location='view_args',
            validate=validate.Range(min=1, max=2147483647)),
        'review_id': fields.Int(
            required=True, validate=validate.Range(min=1, max=2147483647)),
        'fields': fields.DelimitedList(
            fields.String(), delimiter=',',
            missing=['citation_id', 'authors', 'title', 'abstract', 'publication_year', 'doi'])
        })
    def get(self, citation_id, review_id, fields):
        query = """
            SELECT %(fields)s
            FROM citations
            WHERE
                citation_id = %(citation_id)s
                AND review_id = %(review_id)s
            """
        bindings = {'fields': AsIs(','.join(fields)),
                    'review_id': review_id,
                    'citation_id': citation_id}
        result = list(PGDB.run_query(query, bindings=bindings))
        if not result:
            raise Exception()
        return result[0]


class Citations(Resource):

    @use_kwargs({
        'review_id': fields.Int(
            required=True, validate=validate.Range(min=1, max=2147483647)),
        'fields': fields.DelimitedList(
            fields.String(), delimiter=',',
            missing=['citation_id', 'authors', 'title', 'abstract', 'publication_year', 'doi']),
        'order_dir': fields.String(
            missing='ASC', validate=validate.OneOf(['ASC', 'DESC'])),
        'per_page': fields.Int(
            missing=10, validate=validate.OneOf([10, 20, 50])),
        'page': fields.Int(
            missing=0, validate=validate.Range(min=1)),
        })
    def get(self, review_id, fields, order_dir, per_page, page):
        query = """
            SELECT %(fields)s
            FROM citations
            WHERE review_id = %(review_id)s
            ORDER BY citation_id %(order_dir)s
            LIMIT %(limit)s
            OFFSET %(offset)s
            """
        bindings = {'fields': AsIs(','.join(fields)),
                    'review_id': review_id,
                    'order_dir': AsIs(order_dir),
                    'limit': per_page,
                    'offset': page * per_page}
        return list(PGDB.run_query(query, bindings=bindings))
