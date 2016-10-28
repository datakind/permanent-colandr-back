from operator import itemgetter

from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc, text
from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Length, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants
from ...models import db, Study, Review
from ..errors import forbidden, no_data_found, unauthorized
from ..schemas import StudySchema
from ..authentication import auth


class StudyResource(Resource):

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
        study = db.session.query(Study).get(id)
        if not study:
            return no_data_found('<Study(id={})> not found'.format(id))
        if study.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this study'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        return StudySchema(only=fields).dump(study).data

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        study = db.session.query(Study).get(id)
        if not study:
            return no_data_found('<Study(id={})> not found'.format(id))
        if study.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete this study'.format(g.current_user))
        if test is False:
            db.session.delete(study)
            db.session.commit()

    @swagger.operation()
    @use_args(StudySchema(only=['tags']))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        study = db.session.query(Study).get(id)
        if not study:
            return no_data_found('<Study(id={})> not found'.format(id))
        if study.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to modify this study'.format(g.current_user))
        for key, value in args.items():
            if key != 'tags':
                return forbidden('how are you updating the "{}" field?!'.format(key))
            setattr(study, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return StudySchema().dump(study).data


class StudiesResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String(), delimiter=',', missing=None),
        'tag': ma_fields.String(
            missing=None, validate=Length(max=25)),
        'order_dir': ma_fields.String(
            missing='DESC', validate=OneOf(['ASC', 'DESC'])),
        'per_page': ma_fields.Int(
            missing=25, validate=OneOf([10, 25, 50, 100, 5000])),
        'page': ma_fields.Int(
            missing=0, validate=Range(min=0)),
        })
    def get(self, review_id, fields, tag,
            order_by, order_dir, per_page, page):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get studies from this review'.format(
                    g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        # build the query by components
        query = review.studies
        if tag:
            query = query.filter(Study.tags.any(tag, operator=operators.eq))
        # order, offset, and limit
        order_by = desc(Study.id) if order_dir == 'DESC' else asc(Study.id)
        query = query.order_by(order_by)
        query = query.offset(page * per_page).limit(per_page)
        return StudySchema(many=True, only=fields).dump(query.all()).data
