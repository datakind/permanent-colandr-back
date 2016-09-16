from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_args, use_kwargs

from ..lib import constants
from ..models import db, CitationScreening, Citation, Review, User
from .errors import unauthorized
from .schemas import ScreeningSchema
from .authentication import auth


class CitationScreeningsResource(Resource):

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
        if citation_id is not None:
            citation = db.session.query(Citation).get(citation_id)
            if not citation:
                raise NoResultFound
            query = citation.screenings
        elif user_id is not None:
            user = db.session.query(User).get(user_id)
            if not user:
                raise NoResultFound
            query = user.citation_screenings
        elif review_id is not None:
            review = db.session.query(Review).get(review_id)
            if not review:
                raise NoResultFound
            query = review.citation_screenings
        else:
            raise ValueError()
        if status_counts is True:
            query = query.with_entities(CitationScreening.status, db.func.count(1))\
                .group_by(CitationScreening.status)
            return dict(query.all())
        return ScreeningSchema(partial=True, many=True).dump(query.all()).data

    @swagger.operation()
    @use_args(ScreeningSchema(partial=['user_id', 'fulltext_id']))
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        # check current user authorization
        review = db.session.query(Review).get(args['review_id'])
        if not review:
            raise NoResultFound
        if g.current_user.reviews.filter_by(id=args['review_id']).one_or_none() is None:
            return unauthorized(
                '{} not authorized to screen citations for {}'.format(
                    g.current_user, review))
        # initialize and add the screening
        screening = CitationScreening(
            args['review_id'], g.current_user.id, args['citation_id'],
            args['status'], args['exclude_reasons'])
        db.session.add(screening)
        # update associated citation status, considering all screenings
        citation = db.session.query(Citation).get(args['citation_id'])
        all_screenings = citation.screenings
        num_screeners = review.num_citation_screening_reviewers
        if num_screeners == 1:
            citation.status = screening.status
        elif len(all_screenings) < num_screeners:
            if len(all_screenings) == 1:
                citation.status = 'screened_once'
            else:
                citation.status = 'screened_twice'
        else:
            if all(scrn.status == 'included' for scrn in all_screenings):
                citation.status = 'included'
            elif all(scrn.status == 'excluded' for scrn in all_screenings):
                citation.status = 'excluded'
            else:
                citation.status = 'conflict'
        import logging
        logging.warning('!!!!! citation.status = %s', citation.status)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return ScreeningSchema().dump(screening).data
