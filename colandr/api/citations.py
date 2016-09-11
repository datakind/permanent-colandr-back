import flask
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..models import db, Citation
from .schemas import CitationSchema
from .authentication import auth
import cipy


class CitationsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, review_id, test):
        # TODO: check if current user has permissions for this review
        fname = uploaded_file.filename
        if fname.endswith('.bib'):
            citations_file = cipy.parsers.BibTexFile(uploaded_file.stream)
        elif fname.endswith('.ris') or fname.endswith('.txt'):
            citations_file = cipy.parsers.RisFile(uploaded_file.stream)
        else:
            raise TypeError()
        citation_schema = CitationSchema()
        for record in citations_file.parse():
            record['review_id'] = review_id
            citation_data = citation_schema.dump(record).data
            citation = Citation(**citation_data)
            if test is False:
                db.session.add(citation)
        if test is False:
            db.session.commit()  # TODO: bulk_insert_mappings?


# class Citations(Resource):
#
#     @swagger.operation()
#     @use_kwargs({
#         'review_id': fields.Int(
#             required=True, validate=validate.Range(min=1, max=2147483647)),
#         'fields': fields.DelimitedList(
#             fields.String(), delimiter=',',
#             missing=['citation_id', 'authors', 'title', 'abstract', 'publication_year', 'doi']),
#         'status': fields.String(
#             missing='', validate=validate.OneOf(['included', 'excluded', ''])),
#         'order_dir': fields.String(
#             missing='ASC', validate=validate.OneOf(['ASC', 'DESC'])),
#         'per_page': fields.Int(
#             missing=10, validate=validate.OneOf([10, 20, 50])),
#         'page': fields.Int(
#             missing=0, validate=validate.Range(min=0)),
#         })
#     def get(self, review_id, fields, status, order_dir, per_page, page):
#         bindings = {'review_id': review_id,
#                     'order_dir': AsIs(order_dir),
#                     'limit': per_page,
#                     'offset': page * per_page}
#         if status:
#             query = """
#                 SELECT %(fields)s
#                 FROM
#                     citations AS t1,
#                     citation_status AS t2
#                 WHERE
#                     t1.review_id = %(review_id)s
#                     AND t1.citation_id = t2.citation_id
#                     AND t2.status = %(status)s
#                 ORDER BY t1.citation_id %(order_dir)s
#                 LIMIT %(limit)s
#                 OFFSET %(offset)s
#                 """
#             bindings['fields'] = AsIs(','.join('t1.' + field for field in fields))
#             bindings['status'] = status
#         else:
#             query = """
#                 SELECT %(fields)s
#                 FROM citations
#                 WHERE review_id = %(review_id)s
#                 ORDER BY citation_id %(order_dir)s
#                 LIMIT %(limit)s
#                 OFFSET %(offset)s
#                 """
#             bindings['fields'] = AsIs(','.join(fields))
#
#         return list(PGDB.run_query(query, bindings=bindings))
