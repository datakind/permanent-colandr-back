from operator import itemgetter

from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc, text
from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow import ValidationError
from marshmallow.validate import OneOf, Length, Range, URL
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants
from ...lib.nlp import reviewer_terms
from ...models import db, Citation, DataSource, Review, Study
from ..errors import forbidden, no_data_found, unauthorized, validation
from ..schemas import CitationSchema, DataSourceSchema
from ..authentication import auth


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
        if (g.current_user.is_admin is False and
                citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get this citation'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
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
            if key is missing or key == 'other_fields':
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

    @swagger.operation()
    @use_args(CitationSchema(partial=True))
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'source_type': ma_fields.Str(
            required=True, validate=OneOf(['database', 'gray literature'])),
        'source_name': ma_fields.Str(
            missing=None, validate=Length(max=100)),
        'source_url': ma_fields.Str(
            missing=None, validate=[URL(relative=False), Length(max=500)]),
        'status': ma_fields.Str(
            missing=None, validate=OneOf(['not_screened', 'included', 'excluded'])),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, args, review_id, source_type, source_name, source_url,
             status, test):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to add citations to this review'.format(g.current_user))

        # upsert the data source
        try:
            DataSourceSchema().validate(
                {'source_type': source_type,
                 'source_name': source_name,
                 'source_url': source_url})
        except ValidationError as e:
            return validation(e.messages)
        data_source = db.session.query(DataSource)\
            .filter_by(source_type=source_type, source_name=source_name).one_or_none()
        if data_source is None:
            data_source = DataSource(source_type, source_name, source_url=source_url)
            db.session.add(data_source)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
            return ''

        # add the study
        study = Study(g.current_user.id, review_id, data_source.id)
        if status is not None:
            study.citation_status = status
        db.session.add(study)
        db.session.commit()

        # *now* add the citation
        citation = args
        citation = CitationSchema().load(citation).data  # this sanitizes the data
        citation = Citation(study.id, **citation)
        db.session.add(citation)
        db.session.commit()

        # TODO: what about deduplication?!
        # TODO: what about adding *multiple* citations via this endpoint?

        return CitationSchema().dump(citation).data
