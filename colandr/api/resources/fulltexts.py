from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc, text
from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow.validate import Length, OneOf, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs
from webargs import missing

from ...lib import constants
from ...models import db, Citation, Fulltext, Review
from ..errors import forbidden, no_data_found, unauthorized
from ..schemas import FulltextSchema
from ..authentication import auth


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
            elif key == 'status':
                return forbidden('fulltext status can not be updated manually')
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
            missing=25, validate=OneOf([10, 25, 50, 100, 1000])),
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
        if fields and 'id' not in fields:
            fields.append('id')
        # build the query by components
        query = review.fulltexts
        # filters
        if status:
            if status in ('conflict', 'excluded', 'included'):
                query = query.filter(Fulltext.status == status)
            elif status == 'pending':
                sql_query = """
                    SELECT t.id
                    FROM (SELECT fulltexts.id, fulltexts.status, screenings.user_ids
                          FROM fulltexts
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON fulltexts.id = screenings.fulltext_id
                          ) AS t
                    WHERE
                        t.status = 'not_screened'
                        OR NOT {user_id} = ANY(t.user_ids)
                    """.format(user_id=g.current_user.id)
                query = query.filter(Fulltext.id.in_(text(sql_query)))
            elif status == 'awaiting_coscreener':
                sql_query = """
                    SELECT t.id
                    FROM (SELECT fulltexts.id, fulltexts.status, screenings.user_ids
                          FROM fulltexts
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON fulltexts.id = screenings.fulltext_id
                          ) AS t
                    WHERE
                        t.status IN ('screened_once', 'screened_twice')
                        AND {user_id} = ANY(t.user_ids)
                    """.format(user_id=g.current_user.id)
                query = query.filter(Fulltext.id.in_(text(sql_query)))
        if tag:
            query = query.filter(Fulltext.citation.tags.any(tag, operator=operators.eq))
        if tsquery:
            query = query.filter(Fulltext.content.match(tsquery))
        # order, offset, and limit
        order_by = Fulltext.id if order_by == 'recency' else Fulltext.id  # TODO: NLP!
        order_by = desc(order_by) if order_dir == 'DESC' else asc(order_by)
        query = query.order_by(order_by)
        query = query.offset(page * per_page).limit(per_page)
        return FulltextSchema(many=True, only=fields).dump(query.all()).data
