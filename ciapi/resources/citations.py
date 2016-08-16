from flask import request
from flask_restful import Resource
from psycopg2.extensions import AsIs
from webargs import fields as fields
from webargs.flaskparser import use_args, use_kwargs

from ciapi import PGDB


get_citation_args = {
    'citation_id': fields.Int(
        required=True, location='view_args'),
    'review_id': fields.Int(required=True),
    'fields': fields.DelimitedList(
        fields.String(),
        delimiter=',',
        missing=['citation_id', 'authors', 'title', 'abstract', 'publication_year', 'doi'])
    }


class Citation(Resource):

    @use_kwargs(get_citation_args)
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
