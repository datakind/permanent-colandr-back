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
from webargs.flaskparser import use_kwargs

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
            validate=OneOf(['planning', 'citations', 'fulltexts', 'extraction', 'all']),
            missing='all'),
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
                query = """
                    SELECT
                        (CASE
                             WHEN status IN ('included', 'excluded', 'conflict') THEN status
                             WHEN status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                             WHEN status IN ('screened_once', 'screened_twice') AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                         END) AS user_status,
                         COUNT(1)
                    FROM (SELECT citations.id, citations.status, screenings.user_ids
                          FROM citations
                          LEFT JOIN (SELECT citation_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM citation_screenings
                                     GROUP BY citation_id
                                     ) AS screenings
                          ON citations.id = screenings.citation_id
                          ) AS t
                    GROUP BY user_status;
                    """.format(user_id=g.current_user.id)
                progress = [row for row in db.engine.execute(query)]
            response['citations'] = dict(progress)
        if step in ('fulltexts', 'all'):
            if user_view is False:
                progress = db.session.query(Fulltext.status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .group_by(Fulltext.status)\
                    .all()
            else:
                query = """
                    SELECT
                        (CASE
                             WHEN status IN ('included', 'excluded', 'conflict') THEN status
                             WHEN status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                             WHEN status IN ('screened_once', 'screened_twice') AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                         END) AS user_status,
                         COUNT(1)
                    FROM (SELECT fulltexts.id, fulltexts.status, screenings.user_ids
                          FROM fulltexts
                          LEFT JOIN (SELECT fulltext_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM fulltext_screenings
                                     GROUP BY fulltext_id
                                     ) AS screenings
                          ON fulltexts.id = screenings.fulltext_id
                          ) AS t
                    GROUP BY user_status;
                    """.format(user_id=g.current_user.id)
                progress = [row for row in db.engine.execute(query)]
            response['fulltexts'] = dict(progress)
        if step == 'extraction':
            # TODO
            raise NotImplementedError('working on it! -- Burton')

        return response
