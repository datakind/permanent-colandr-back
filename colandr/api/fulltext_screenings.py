import itertools
import logging
from operator import attrgetter

from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..lib import constants
from ..models import db, FulltextScreening, Fulltext, Review, User
from .errors import bad_request, forbidden, no_data_found, unauthorized, validation
from .schemas import ScreeningSchema
from .utils import assign_status
from .authentication import auth


class FulltextScreeningsResource(Resource):

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
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get fulltext screenings for this review'.format(
                    g.current_user))
        return ScreeningSchema(many=True, only=fields).dump(fulltext.screenings).data

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_BIGINT)),
        'test': ma_fields.Boolean(missing=False),
        })
    def delete(self, id, test):
        # check current user authorization
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to delete fulltext screening for this review'.format(
                    g.current_user))
        screening = fulltext.screenings.filter_by(user_id=g.current_user.id).one_or_none()
        if not screening:
            return forbidden('{} has not screened {}, so nothing to delete'.format(
                g.current_user, fulltext))
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
        fulltext = db.session.query(Fulltext).get(id)
        if not fulltext:
            return no_data_found('<Fulltext(id={})> not found'.format(id))
        if g.current_user.reviews.filter_by(id=fulltext.review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to screen fulltexts for this review'.format(
                    g.current_user))
        if fulltext.filename is None:
            return forbidden(
                "user can't scree {} without first having uploaded its content".format(
                    fulltext))
        # validate and add screening
        if args['status'] == 'excluded' and not args['exclude_reasons']:
            return validation('screenings that exclude must provide a reason')
        screening = FulltextScreening(
            fulltext.review_id, g.current_user.id, id,
            args['status'], args['exclude_reasons'])
        if fulltext.screenings.filter_by(user_id=g.current_user.id).one_or_none():
            return forbidden('{} has already screened {}'.format(
                g.current_user, fulltext))
        if test is False:
            fulltext.screenings.append(screening)
            db.session.commit()
        else:
            db.session.rollback()
        return ScreeningSchema().dump(screening).data


class FulltextsScreeningsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'fulltext_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_BIGINT)),
        'user_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'review_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'status_counts': ma_fields.Bool(missing=False),
        })
    def get(self, fulltext_id, user_id, review_id, status_counts):
        if not any([fulltext_id, user_id, review_id]):
            return bad_request('fulltext, user, and/or review id must be specified')
        query = db.session.query(FulltextScreening)
        if fulltext_id is not None:
            # check user authorization
            fulltext = db.session.query(Fulltext).get(fulltext_id)
            if not fulltext:
                return no_data_found(
                    '<Fulltext(id={})> not found'.format(fulltext_id))
            if fulltext.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
                return unauthorized(
                    '{} not authorized to get screenings for {}'.format(
                        g.current_user, fulltext))
            query = query.filter_by(fulltext_id=fulltext_id)
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
                .with_entities(FulltextScreening.status, db.func.count(1))\
                .group_by(FulltextScreening.status)
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
        # check current user authorization
        review = db.session.query(Review).get(review_id)
        if not review:
            return no_data_found(
                '<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=review_id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to screen fulltexts for {}'.format(
                    g.current_user, review))
        # bulk insert fulltext screenings
        user_id = g.current_user.id
        screenings_to_insert = []
        for screening in args:
            screening['review_id'] = review_id
            screening['user_id'] = user_id
            screenings_to_insert.append(screening)
        if test is False:
            db.session.bulk_insert_mappings(
                FulltextScreening, screenings_to_insert)
            db.session.commit()
        # bulk update fulltext statuses
        num_screeners = review.num_fulltext_screening_reviewers
        fulltext_ids = sorted(s['fulltext_id'] for s in screenings_to_insert)
        results = db.session.query(FulltextScreening)\
            .filter(FulltextScreening.fulltext_id.in_(fulltext_ids))
        fulltexts_to_update = [
            {'id': fid, 'status': assign_status(list(scrns), num_screeners)}
            for fid, scrns in itertools.groupby(results, attrgetter('fulltext_id'))
            ]
        if test is False:
            db.session.bulk_update_mappings(
                Fulltext, fulltexts_to_update)
            db.session.commit()
