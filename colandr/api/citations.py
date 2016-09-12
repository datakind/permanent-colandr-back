from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..lib import constants
from ..lib.parsers import BibTexFile, RisFile
from ..models import db, Citation, Review
from .errors import unauthorized
from .schemas import CitationSchema
from .authentication import auth


class CitationResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'citation_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, citation_id, fields):
        citation = db.session.query(Citation).get(citation_id)
        if not citation:
            raise NoResultFound
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this citation'.format(g.current_user))
        return CitationSchema(only=fields).dump(citation).data

    @swagger.operation()
    @use_kwargs({
        'citation_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, citation_id, test):
        citation = db.session.query(Citation).get(citation_id)
        if not citation:
            raise NoResultFound
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete this citation'.format(g.current_user))
        if test is False:
            db.session.delete(citation)
            db.session.commit()

    @swagger.operation()
    @use_args(CitationSchema(partial=True))
    @use_kwargs({
        'citation_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, citation_id, test):
        citation = db.session.query(Citation).get(citation_id)
        if not citation:
            raise NoResultFound
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete this citation'.format(g.current_user))
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(citation, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return CitationSchema().dump(citation).data


class CitationsResource(Resource):

    method_decorators = [auth.login_required]

    # @swagger.operation()
    # @use_kwargs()
    # def get(self, review_id):
    #     raise NotImplementedError('sorry')

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, review_id, test):
        review = db.session.query(Review).get(review_id)
        if not review:
            raise NoResultFound
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add citations to this review'.format(g.current_user))
        fname = uploaded_file.filename
        if fname.endswith('.bib'):
            citations_file = BibTexFile(uploaded_file.stream)
        elif fname.endswith('.ris') or fname.endswith('.txt'):
            citations_file = RisFile(uploaded_file.stream)
        else:
            raise TypeError()
        citation_schema = CitationSchema()

        citations_to_insert = []
        for record in citations_file.parse():
            record['review_id'] = review_id
            citation_data = citation_schema.load(record).data
            citations_to_insert.append(Citation(**citation_data))
        if test is False:
            db.session.bulk_save_objects(citations_to_insert)


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
