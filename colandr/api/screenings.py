from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..lib import constants
from ..models import db, CitationScreening, Citation, Review, User
from .errors import bad_request, forbidden, no_data_found, unauthorized, validation
from .schemas import ScreeningSchema
from .authentication import auth


def assign_citation_status(screenings, num_screeners):
    num_screenings = len(screenings)
    if num_screenings == 0:
        return 'not_screened'
    elif num_screenings < num_screeners:
        if num_screenings == 1:
            return 'screened_once'
        else:
            return 'screened_twice'
    else:
        statuses = tuple(screening.status for screening in screenings)
        if all(status == 'excluded' for status in statuses):
            return 'excluded'
        elif all(status == 'included' for status in statuses):
            return 'included'
        else:
            return 'conflict'


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
        citation.status = assign_citation_status(
            citation.screenings.all(), citation.review.num_citation_screening_reviewers)
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
        if test is False:
            citation.screenings.append(screening)
            citation.status = assign_citation_status(
                citation.screenings.all(), citation.review.num_citation_screening_reviewers)
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
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, args, review_id, test):
        # check current user authorization
        review = db.session.query(Review).get(args['review_id'])
        if not review:
            return no_data_found(
                '<Review(id={})> not found'.format(review_id))
        if g.current_user.reviews.filter_by(id=args['review_id']).one_or_none() is None:
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
        # bulk update citation statuses
        num_screeners = review.num_citation_screening_reviewers
        citations_to_update = []
        for screening in screenings_to_insert:
            citation = db.session.query(Citation).get(screening['citation_id'])
            status = assign_citation_status(
                citation.screenings.all(), num_screeners)
            citations_to_update.append(
                {'id': screening['citation_id'], 'status': status})
        if test is False:
            db.session.bulk_update_mappings(
                Citation, citations_to_update)
