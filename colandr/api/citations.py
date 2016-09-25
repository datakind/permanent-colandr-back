from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc
from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Length, Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..lib import constants
from ..lib.parsers import BibTexFile, RisFile
from ..models import db, Citation, Fulltext, Review
from .errors import forbidden, no_data_found, unauthorized, validation
from .schemas import CitationSchema
from .authentication import auth


class CitationResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
        citation = db.session.query(Citation).get(id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(id))
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this citation'.format(g.current_user))
        return CitationSchema(only=fields).dump(citation).data

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        citation = db.session.query(Citation).get(id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(id))
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete this citation'.format(g.current_user))
        if test is False:
            db.session.delete(citation)
            db.session.commit()

    @swagger.operation()
    @use_args(CitationSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        citation = db.session.query(Citation).get(id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(id))
        if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to modify this citation'.format(g.current_user))
        for key, value in args.items():
            if key is missing:
                continue
            elif key == 'status':
                return forbidden('citation status can not be updated manually')
            else:
                setattr(citation, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return CitationSchema().dump(citation).data


class CitationsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String(), delimiter=',', missing=None),
        'tsquery': ma_fields.String(
            missing=None, validate=Length(max=50)),
        'status': ma_fields.String(
            missing=None, validate=OneOf(['pending', 'awaiting_coscreener',
                                          'conflict', 'excluded', 'included'])),
        'tag': ma_fields.String(
            missing=None, validate=Length(max=25)),
        'order_by': ma_fields.String(
            missing='recency', validate=OneOf(['recency', 'relevance'])),
        'order_dir': ma_fields.String(
            missing='DESC', validate=OneOf(['ASC', 'DESC'])),
        'per_page': ma_fields.Int(
            missing=25, validate=OneOf([10, 25, 50])),
        'page': ma_fields.Int(
            missing=0, validate=Range(min=0)),
        })
    def get(self, review_id, fields, status, tag, tsquery,
            order_by, order_dir, per_page, page):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get citations from this review'.format(
                    g.current_user))
        # build the query by components
        query = review.citations
        # filters
        if status:
            if status in ('conflict', 'excluded', 'included'):
                query = query.filter(Citation.status == status)
            elif status == 'pending':
                raise NotImplementedError('working on it')
            elif status == 'awaiting_coscreener':
                raise NotImplementedError('working on it')
        if tag:
            query = query.filter(Citation.tags.any(tag, operator=operators.eq))
        if tsquery:
            query = query.filter(Citation.text_content.match(tsquery))
        # order, offset, and limit
        order_by = Citation.id if order_by == 'recency' else Citation.id  # TODO: NLP!
        order_by = desc(order_by) if order_dir == 'DESC' else asc(order_by)
        query = query.order_by(order_by)
        query = query.offset(page * per_page).limit(per_page)
        # get particular columns or full citations
        if fields:
            if 'id' not in fields:
                fields.append('id')
            fields = sorted(fields)
            query = query.with_entities(*[getattr(Citation, field) for field in fields])
            results = [{field: value for field, value in zip(fields, row)}
                       for row in query]
        else:
            results = query.all()
        return CitationSchema(many=True).dump(results).data

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'status': ma_fields.Str(
            missing=None, validate=OneOf(['included', 'excluded'])),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, review_id, status, test):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add citations to this review'.format(g.current_user))
        fname = uploaded_file.filename
        if fname.endswith('.bib'):
            citations_file = BibTexFile(uploaded_file.stream)
        elif fname.endswith('.ris') or fname.endswith('.txt'):
            citations_file = RisFile(uploaded_file.stream)
        else:
            return validation('unknown file type: "{}"'.format(fname))
        citation_schema = CitationSchema()
        citations_to_insert = []
        fulltexts_to_insert = []
        for record in citations_file.parse():
            record['review_id'] = review_id
            if status:
                record['status'] = status
                if status == 'included':
                    fulltexts_to_insert.append(
                        Fulltext(record['review_id'], record['citation_id']))
            citation_data = citation_schema.load(record).data
            citations_to_insert.append(Citation(**citation_data))
        if test is False:
            db.session.bulk_save_objects(citations_to_insert)
            if status == 'included':
                db.session.bulk_save_objects(fulltexts_to_insert)
