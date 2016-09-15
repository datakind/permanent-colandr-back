from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
# from marshmallow.validate import Range
from webargs.flaskparser import use_args, use_kwargs

# from ..lib import constants
from ..models import db, CitationScreening, Citation, Review
from .errors import unauthorized
from .schemas import ScreeningSchema
from .authentication import auth


class CitationScreeningsResource(Resource):

    method_decorators = [auth.login_required]

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
