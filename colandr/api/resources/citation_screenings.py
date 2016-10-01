import logging

from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants
from ...models import db, Citation, CitationScreening, Fulltext, Review, User
from ..errors import bad_request, forbidden, no_data_found, unauthorized, validation
from ..schemas import ScreeningSchema
from ..utils import assign_status
from ..authentication import auth


class CitationScreeningsResource(Resource):

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
        # check current user authorization
        citation = db.session.query(Citation).get(id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=citation.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get citation screenings for this review'.format(
                    g.current_user))
        return ScreeningSchema(many=True, only=fields).dump(citation.screenings).data

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False),
        })
    def delete(self, id, test):
        # check current user authorization
        citation = db.session.query(Citation).get(id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=citation.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete citation screening for this review'.format(
                    g.current_user))
        screening = citation.screenings.filter_by(user_id=g.current_user.id).one_or_none()
        if not screening:
            return forbidden('{} has not screened {}, so nothing to delete'.format(
                g.current_user, citation))
        db.session.delete(screening)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()

    @swagger.operation()
    @use_args(ScreeningSchema(partial=['user_id', 'review_id']))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False),
        })
    def post(self, args, id, test):
        # check current user authorization
        citation = db.session.query(Citation).get(id)
        if not citation:
            return no_data_found('<Citation(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=citation.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to screen citations for this review'.format(
                    g.current_user))
        # validate and add screening
        if args['status'] == 'excluded' and not args['exclude_reasons']:
            return validation('screenings that exclude must provide a reason')
        screening = CitationScreening(
            citation.review_id, g.current_user.id, id,
            args['status'], args['exclude_reasons'])
        if citation.screenings.filter_by(user_id=g.current_user.id).one_or_none():
            return forbidden('{} has already screened {}'.format(
                g.current_user, citation))
        citation.screenings.append(screening)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return ScreeningSchema().dump(screening).data


class CitationsScreeningsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'citation_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_BIGINT)),
        'user_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'review_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'status_counts': ma_fields.Bool(missing=False),
        })
    def get(self, citation_id, user_id, review_id, status_counts):
        if not any([citation_id, user_id, review_id]):
            return bad_request('citation, user, and/or review id must be specified')
        query = db.session.query(CitationScreening)
        if citation_id is not None:
            # check user authorization
            citation = db.session.query(Citation).get(citation_id)
            if not citation:
                return no_data_found(
                    '<Citation(id={})> not found'.format(citation_id))
            if citation.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
                return unauthorized(
                    '{} not authorized to get screenings for {}'.format(
                        g.current_user, citation))
            query = query.filter_by(citation_id=citation_id)
        if user_id is not None:
            # check user authorization
            user = db.session.query(User).get(user_id)
            if not user:
                return no_data_found(
                    '<User(id={})> not found'.format(user_id))
            if not any(user_id == user.id
                       for review in g.current_user.reviews
                       for user in review.users):
                return unauthorized(
                    '{} not authorized to get screenings for {}'.format(
                        g.current_user, user))
            query = query.filter_by(user_id=user_id)
        if review_id is not None:
            # check user authorization
            review = db.session.query(Review).get(review_id)
            if not review:
                return no_data_found(
                    '<Review(id={})> not found'.format(review_id))
            if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
                return unauthorized(
                    '{} not authorized to get screenings for {}'.format(
                        g.current_user, review))
            query = query.filter_by(review_id=review_id)
        if status_counts is True:
            query = query\
                .with_entities(CitationScreening.status, db.func.count(1))\
                .group_by(CitationScreening.status)
            return dict(query.all())
        return ScreeningSchema(partial=True, many=True).dump(query.all()).data

    @swagger.operation()
    @use_args(ScreeningSchema(many=True, partial=['user_id', 'review_id']))
    @use_kwargs({
        'review_id': ma_fields.Int(
            location='query',
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(
            location='query', missing=False)
        })
    def post(self, args, review_id, test):
        logging.warning('the "citations/screenings" endpoint is for dev use only')
        # check current user authorization
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found(
                '<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to screen citations for {}'.format(
                    g.current_user, review))
        # bulk insert citation screenings
        user_id = g.current_user.id
        screenings_to_insert = []
        for screening in args:
            screening['review_id'] = review_id
            screening['user_id'] = user_id
            screenings_to_insert.append(screening)
        if test is False:
            db.session.bulk_insert_mappings(
                CitationScreening, screenings_to_insert)
            db.session.commit()
        # bulk update citation statuses
        num_screeners = review.num_citation_screening_reviewers
        citation_ids = sorted(s['citation_id'] for s in screenings_to_insert)
        # results = db.session.query(CitationScreening)\
        #     .filter(CitationScreening.citation_id.in_(citation_ids))
        # citations_to_update = [
        #     {'id': cid, 'status': assign_status(list(scrns), num_screeners)}
        #     for cid, scrns in itertools.groupby(results, attrgetter('citation_id'))
        #     ]
        with db.engine.connect() as connection:
            query = """
                SELECT citation_id, ARRAY_AGG(status)
                FROM citation_screenings
                WHERE citation_id IN ({citation_ids})
                GROUP BY citation_id
                ORDER BY citation_id
                """.format(citation_ids=','.join(str(cid) for cid in citation_ids))
            results = connection.execute(query)
        citations_to_update = [
            {'id': row[0], 'status': assign_status(row[1], num_screeners)}
            for row in results]
        if test is False:
            db.session.bulk_update_mappings(
                Citation, citations_to_update)
            db.session.commit()
            # add fulltexts for included citations
            cids_need_fulltexts = """
                SELECT citations.id
                FROM citations
                LEFT JOIN fulltexts ON citations.id = fulltexts.citation_id
                WHERE
                    citations.review_id = {review_id}
                    AND citations.status = 'included'
                    AND fulltexts.id IS NULL
                ORDER BY citations.id
                """.format(review_id=review_id)
            citation_ids = [row[0] for row in db.engine.execute(cids_need_fulltexts)]
            for cid in citation_ids:
                db.session.add(Fulltext(review_id, cid))
            db.session.commit()
