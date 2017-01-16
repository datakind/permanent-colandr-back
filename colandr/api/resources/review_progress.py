from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.flaskparser import use_kwargs

from ...lib import constants
from ...models import db, Review, Study
from ..errors import no_data_found, unauthorized
from ..authentication import auth

SCREENING_STATUSES = (
    'not_screened', 'screened_once', 'conflict', 'included', 'excluded')
USER_SCREENING_STATUSES = (
    'pending', 'awaiting_coscreener', 'conflict', 'included', 'excluded')
EXTRACTION_STATUSES = (
    'not_started', 'started', 'finished')


class ReviewProgressResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'step': ma_fields.Str(
            validate=OneOf(['planning', 'citation_screening', 'fulltext_screening',
                            'data_extraction', 'all']),
            missing='all'),
        'user_view': ma_fields.Bool(missing=False),
        })
    def get(self, id, step, user_view):
        response = {}
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
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
            response['planning'] = progress  # {key: val for key, val in progress.items()}
        if step in ('citation_screening', 'all'):
            if user_view is False:
                progress = db.session.query(Study.citation_status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .group_by(Study.citation_status)\
                    .all()
                progress = dict(progress)
                progress = {status: progress.get(status, 0)
                            for status in SCREENING_STATUSES}
            else:
                query = """
                    SELECT
                        (CASE
                             WHEN citation_status IN ('included', 'excluded', 'conflict') THEN citation_status
                             WHEN citation_status = 'screened_once' AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                             WHEN citation_status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                         END) AS user_status,
                         COUNT(*)
                    FROM (SELECT studies.id, studies.citation_status, screenings.user_ids
                          FROM studies
                          LEFT JOIN (SELECT citation_id, ARRAY_AGG(user_id) AS user_ids
                                     FROM citation_screenings
                                     GROUP BY citation_id
                                     ) AS screenings
                          ON studies.id = screenings.citation_id
                          WHERE review_id = {review_id}
                          ) AS t
                    GROUP BY user_status;
                    """.format(user_id=g.current_user.id, review_id=id)
                progress = dict(row for row in db.engine.execute(query))
                progress = {status: progress.get(status, 0)
                            for status in USER_SCREENING_STATUSES}
            response['citation_screening'] = progress
        if step in ('fulltext_screening', 'all'):
            if user_view is False:
                progress = db.session.query(Study.fulltext_status, db.func.count(1))\
                    .filter_by(review_id=id)\
                    .filter_by(citation_status='included')\
                    .group_by(Study.fulltext_status)\
                    .all()
                progress = dict(progress)
                progress = {status: progress.get(status, 0)
                            for status in SCREENING_STATUSES}
            else:
                query = """
                    SELECT
                        (CASE
                             WHEN fulltext_status IN ('included', 'excluded', 'conflict') THEN fulltext_status
                             WHEN fulltext_status = 'not_screened' OR NOT {user_id} = ANY(user_ids) THEN 'pending'
                             WHEN fulltext_status = 'screened_once' AND {user_id} = ANY(user_ids) THEN 'awaiting_coscreener'
                         END) AS user_status,
                         COUNT(*)
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
                          WHERE review_id = {review_id}
                          ) AS t
                    WHERE citation_status = 'included'  -- this is necessary!
                    GROUP BY user_status;
                    """.format(user_id=g.current_user.id, review_id=id)
                progress = dict(row for row in db.engine.execute(query))
                progress = {status: progress.get(status, 0)
                            for status in USER_SCREENING_STATUSES}
            response['fulltext_screening'] = progress
        if step in ('data_extraction', 'all'):
            progress = db.session.query(Study.data_extraction_status, db.func.count(1))\
                .filter_by(review_id=id)\
                .filter_by(fulltext_status='included')\
                .group_by(Study.data_extraction_status)\
                .all()
            progress = dict(progress)
            progress = {status: progress.get(status, 0)
                        for status in EXTRACTION_STATUSES}
            response['data_extraction'] = progress

        return response
