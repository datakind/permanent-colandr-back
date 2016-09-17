from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy import asc, desc, and_, or_
from sqlalchemy.orm.exc import NoResultFound
# from sqlalchemy.sql import operators

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
# from webargs import missing
# from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..lib import constants
from ..models import db, Citation, Fulltext, Review
from .errors import unauthorized
from .authentication import auth


class ReviewProgressResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'step': ma_fields.Str(
            missing='all', validate=OneOf(['planning', 'citations', 'fulltexts',
                                           'extraction', 'all'])),
        'user_view': ma_fields.Bool(missing=False),
        })
    def get(self, id, step, user_view):
        response = {}
        review = db.session.query(Review).get(id)
        if not review:
            raise NoResultFound
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get review progress'.format(g.current_user))
        if step in ('planning', 'all'):
            review_plan = review.review_plan
            progress = {'objective': bool(review_plan.objective),
                        'research_questions': bool(review_plan.research_questions),
                        'pico': bool(review_plan.pico),
                        'keyterms': bool(review_plan.keyterms),
                        'selection_criteria': bool(review_plan.selection_criteria),
                        'data_extraction_form': bool(review_plan.data_extraction_form),
                        }
            response['planning'] = {key: val for key, val in progress.items()
                                    if val is True}
        if step in ('citations', 'all'):
            if user_view is False:
                progress = db.session.query(Citation.status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .group_by(Citation.status)\
                    .all()
            else:
                progress = db.session.query(Citation.status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .filter(Citation.status.in_(['conflict', 'excluded', 'included']))\
                    .group_by(Citation.status)\
                    .all()
                query = """
                    SELECT
                        (CASE
                             WHEN (status IN ('screened_once', 'screened_twice') AND screening @> '[{{"user_id": {user_id}}}]') THEN 'awaiting_coscreener'
                             WHEN (status = 'not_screened' OR NOT screening @> '[{{"user_id": {user_id}}}]') THEN 'pending'
                         END) AS user_view_status,
                         COUNT(1)
                    FROM citations
                    GROUP BY 1""".format(user_id=g.current_user.id)
                progress.extend(row for row in db.engine.execute(query))
            response['citations'] = dict(progress)
        if step in ('fulltexts', 'all'):
            if user_view is False:
                progress = db.session.query(Fulltext.status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .group_by(Fulltext.status)\
                    .all()
            else:
                progress = db.session.query(Fulltext.status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .filter(Citation.status.in_(['conflict', 'excluded', 'included']))\
                    .group_by(Fulltext.status)\
                    .all()
                query = """
                    SELECT
                        (CASE
                             WHEN (status IN ('screened_once', 'screened_twice') AND screening @> '[{{"user_id": {user_id}}}]') THEN 'awaiting_coscreener'
                             WHEN (status = 'not_screened' OR NOT screening @> '[{{"user_id": {user_id}}}]') THEN 'pending'
                         END) AS user_view_status,
                         COUNT(1)
                    FROM fulltexts
                    GROUP BY 1""".format(user_id=g.current_user.id)
                progress.extend(row for row in db.engine.execute(query))
            response['fulltexts'] = dict(progress)
        if step == 'extraction':
            # TODO
            raise NotImplementedError('working on it! -- Burton')

        return response
