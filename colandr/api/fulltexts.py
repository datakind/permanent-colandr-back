import os

from flask import current_app, g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc
from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow.validate import Length, OneOf, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs
from webargs import missing

from ..lib import constants
from ..models import db, Citation, Fulltext, Review
from .errors import forbidden, no_data_found, unauthorized, validation
from .schemas import FulltextSchema
from .authentication import auth


class FulltextResource(Resource):

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
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if fulltext.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this fulltext'.format(g.current_user))
        return FulltextSchema(only=fields).dump(fulltext).data

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if fulltext.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete this fulltext'.format(g.current_user))
        if test is False:
            db.session.delete(fulltext)
            db.session.commit()

    @swagger.operation()
    @use_args(FulltextSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if fulltext.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to modify this fulltext'.format(g.current_user))
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(fulltext, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return FulltextSchema().dump(fulltext).data


class FulltextsResource(Resource):

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
                '{} not authorized to get fulltexts from this review'.format(
                    g.current_user))
        # build the query by components
        query = review.fulltexts
        # filters
        if status:
            if status in ('conflict', 'excluded', 'included'):
                query = query.filter(Fulltext.status == status)
            elif status == 'pending':
                raise NotImplementedError('working on it')
            elif status == 'awaiting_coscreener':
                raise NotImplementedError('working on it')
        if tag:
            query = query.filter(Fulltext.citation.tags.any(tag, operator=operators.eq))
        if tsquery:
            query = query.filter(Fulltext.content.match(tsquery))
        # order, offset, and limit
        order_by = Fulltext.id if order_by == 'recency' else Fulltext.id  # TODO: NLP!
        order_by = desc(order_by) if order_dir == 'DESC' else asc(order_by)
        query = query.order_by(order_by)
        query = query.offset(page * per_page).limit(per_page)
        # get particular columns or full citations
        if fields:
            if 'id' not in fields:
                fields.append('id')
            fields = sorted(fields)
            query = query.with_entities(*[getattr(Fulltext, field) for field in fields])
            results = [{field: value for field, value in zip(fields, row)}
                       for row in query]
        else:
            results = query.all()
        return FulltextSchema(many=True).dump(results).data

    @swagger.operation()
    @use_kwargs({
        'uploaded_file': ma_fields.Raw(
            required=True, location='files'),
        'citation_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, uploaded_file, citation_id, test):
        citation = db.session.query(Citation).get(citation_id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(citation_id))
        review_id = citation.review_id
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add fulltexts to this review'.format(g.current_user))
        if citation.status != 'included':
            return forbidden(
                '{} status is not "included", so fulltext can not be uploaded'.format(
                    citation))
        _, ext = os.path.splitext(uploaded_file.filename)
        if ext not in current_app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
            return validation('invalid fulltext upload file type: "{}"'.format(ext))
        filename = '{}{}'.format(citation_id, ext)
        fulltext = Fulltext(review_id, citation_id, filename, content=None)
        if test is False:
            db.session.add(fulltext)
            uploaded_file.save(
                os.path.join(current_app.config['FULLTEXT_UPLOAD_FOLDER'], filename))
            db.session.commit()
        return FulltextSchema().dump(fulltext).data
