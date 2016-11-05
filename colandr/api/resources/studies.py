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

from ...lib import constants, utils
from ...models import db, Citation, Study, Review
from ...lib.nlp import reviewer_terms
from ..errors import forbidden, no_data_found, unauthorized
from ..schemas import StudySchema
from ..authentication import auth


logger = utils.get_console_logger(__name__)


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
        if (g.current_user.is_admin is False and
                study.review.users.filter_by(id=g.current_user.id).one_or_none() is None):
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
        db.session.delete(study)
        if test is False:
            db.session.commit()
            logger.info('deleted %s', study)
        else:
            db.session.rollback()

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
        'citation_status': ma_fields.String(
            missing=None,
            validate=OneOf(['pending', 'awaiting_coscreener', 'conflict', 'excluded', 'included'])),
        'fulltext_status': ma_fields.String(
            missing=None,
            validate=OneOf(['pending', 'awaiting_coscreener', 'conflict', 'excluded', 'included'])),
        'data_extraction_status': ma_fields.String(
            missing=None,
            validate=OneOf(['not_started', 'incomplete', 'complete'])),
        'tag': ma_fields.String(
            missing=None, validate=Length(max=25)),
        'tsquery': ma_fields.String(
            missing=None, validate=Length(max=50)),
        'order_by': ma_fields.String(
            missing='recency', validate=OneOf(['recency', 'relevance'])),
        'order_dir': ma_fields.String(
            missing='DESC', validate=OneOf(['ASC', 'DESC'])),
        'page': ma_fields.Int(
            missing=0, validate=Range(min=0)),
        'per_page': ma_fields.Int(
            missing=25, validate=OneOf([10, 25, 50, 100, 5000])),
        })
    def get(self, review_id, fields,
            citation_status, fulltext_status, data_extraction_status,
            tag, tsquery,
            order_by, order_dir, page, per_page):
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(review_id))
        if (g.current_user.is_admin is False and
                g.current_user.reviews.filter_by(id=review_id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get studies from this review'.format(
                    g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        # build the query by components
        query = review.studies

        if citation_status is not None:
            if citation_status in {'conflict', 'excluded', 'included'}:
                query = query.filter(Study.citation_status == citation_status)
            elif citation_status == 'pending':
                stmt = """
                    SELECT t.id
                    FROM (SELECT studies.id, studies.citation_status, screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT citation_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM citation_screenings
                                     GROUP BY citation_id
                                     ) AS screenings
                          ON studies.id = screenings.citation_id
                          ) AS t
                    WHERE
                        t.citation_status = 'not_screened'
                        OR NOT {user_id} = ANY(t.user_ids)
                    """.format(user_id=g.current_user.id)
                query = query.filter(Study.id.in_(text(stmt)))
            elif citation_status == 'awaiting_coscreener':
                stmt = """
                    SELECT t.id
                    FROM (SELECT studies.id, studies.citation_status, screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT citation_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM citation_screenings
                                     GROUP BY citation_id
                                     ) AS screenings
                          ON studies.id = screenings.citation_id
                          ) AS t
                    WHERE
                        t.citation_status = 'screened_once'
                        AND {user_id} = ANY(t.user_ids)
                    """.format(user_id=g.current_user.id)
                query = query.filter(Study.id.in_(text(stmt)))

        if fulltext_status is not None:
            if fulltext_status in {'conflict', 'excluded', 'included'}:
                query = query.filter(Study.fulltext_status == fulltext_status)
            elif fulltext_status == 'pending':
                stmt = """
                    SELECT t.id
                    FROM (SELECT
                              studies.id,
                              studies.citation_status,
                              studies.fulltext_status,
                              screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON studies.id = screenings.fulltext_id
                          ) AS t
                    WHERE
                        t.citation_status = 'included' -- this is necessary!
                        AND (t.fulltext_status = 'not_screened' OR NOT {user_id} = ANY(t.user_ids))
                    """.format(user_id=g.current_user.id)
                query = query.filter(Study.id.in_(text(stmt)))
            elif fulltext_status == 'awaiting_coscreener':
                stmt = """
                    SELECT t.id
                    FROM (SELECT studies.id, studies.fulltext_status, screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON studies.id = screenings.fulltext_id
                          ) AS t
                    WHERE
                        t.fulltext_status = 'screened_once'
                        AND {user_id} = ANY(t.user_ids)
                    """.format(user_id=g.current_user.id)
                query = query.filter(Study.id.in_(text(stmt)))

        if data_extraction_status is not None:
            if data_extraction_status == 'not_started':
                query = query.filter(Study.data_extraction_status == data_extraction_status)\
                    .filter(Study.fulltext_status == 'included')  # this is necessary!
            else:
                query = query.filter(Study.data_extraction_status == data_extraction_status)

        if tag:
            query = query.filter(Study.tags.any(tag, operator=operators.eq))

        if tsquery:
            if order_by != 'relevance':  # HACK...
                query = query.join(Citation, Citation.id == Study.id)\
                    .filter(Citation.text_content.match(tsquery))

        # order, offset, and limit
        if order_by == 'recency':
            order_by = desc(Study.id) if order_dir == 'DESC' else asc(Study.id)
            query = query.order_by(order_by)
            query = query.offset(page * per_page).limit(per_page)
            return StudySchema(many=True, only=fields).dump(query.all()).data

        elif order_by == 'relevance':
            query = query.join(Citation, Citation.id == Study.id)
            if tsquery:
                query = query.filter(Citation.text_content.match(tsquery))
            results = query.order_by(db.func.random()).limit(1000).all()

            review_plan = review.review_plan
            suggested_keyterms = review_plan.suggested_keyterms
            if suggested_keyterms:
                incl_regex, excl_regex = reviewer_terms.get_incl_excl_terms_regex(
                    review_plan.suggested_keyterms)
                scores = (
                    reviewer_terms.get_incl_excl_terms_score(
                        incl_regex, excl_regex, result.citation.text_content)
                    for result in results)
            else:
                keyterms_regex = reviewer_terms.get_keyterms_regex(
                    review_plan.keyterms)
                scores = (
                    reviewer_terms.get_keyterms_score(
                        keyterms_regex, result.citation.text_content)
                    for result in results)
            sorted_results = [
                result for result, _
                in sorted(zip(results, scores),
                          key=itemgetter(1),
                          reverse=False if order_dir == 'ASC' else True)]
            offset = page * per_page
            return StudySchema(many=True, only=fields).dump(
                sorted_results[offset: offset + per_page]).data
        else:
            raise ValueError()
