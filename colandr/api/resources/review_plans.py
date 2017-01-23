from flask import g
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, utils
from ...models import db, Review
from ..errors import no_data_found, unauthorized, validation
from ..schemas import ReviewPlanSchema
from ..swagger import review_plan_model
from ..authentication import auth
from colandr import api_

logger = utils.get_console_logger(__name__)
ns = api_.namespace(
    'review_plans', path='/reviews/<int:id>/plan',
    description='get, delete, update review plans')


@ns.route('')
@ns.doc(
    summary='get, delete, update review plans',
    produces=['application/json'],
    )
class ReviewPlanResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        params={'fields': {'in': 'query', 'type': 'string',
                           'description': 'comma-delimited list-as-string of review fields to return'},
                },
        responses={200: 'successfully got review plan record',
                   401: 'current app user not authorized to get review plan record',
                   404: 'no review with matching id was found',
                   }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
        """get review plan record for a single review by id"""
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return unauthorized(
                '{} not authorized to get this review plan'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        return ReviewPlanSchema(only=fields).dump(review.review_plan).data

    @ns.doc(
        description='Since review plans are created automatically upon review creation and deleted automatically upon review deletion, "delete" here amounts to nulling out some or all of its non-required fields',
        params={
            'fields': {'in': 'query', 'type': 'string',
                       'description': 'comma-delimited list-as-string of review fields to "delete" (set to null)'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'request was valid, but record not deleted because `test=False`',
            204: 'successfully deleted (nulled) review plan record',
            401: 'current app user not authorized to delete review plan record',
            404: 'no review with matching id was found',
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, fields, test):
        """delete review plan record for a single review by id"""
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to delete this review plan'.format(g.current_user))
        review_plan = review.review_plan
        if fields:
            for field in fields:
                if field == 'objective':
                    review_plan.objective = ''
                elif field == 'pico':
                    review_plan.pico = {}
                else:
                    setattr(review_plan, field, [])
        else:
            review_plan.objective = ''
            review_plan.research_questions = []
            review_plan.pico = {}
            review_plan.keyterms = []
            review_plan.selection_criteria = []
            review_plan.data_extraction_form = []
        if test is False:
            db.session.commit()
            logger.info('deleted contents of %s', review_plan)
            return '', 204
        else:
            db.session.rollback()
            return '', 200

    @ns.doc(
        params={
            'fields': {'in': 'query', 'type': 'string',
                       'description': 'comma-delimited list-as-string of review fields to modify'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        body=(review_plan_model, 'review plan data to be modified'),
        responses={
            200: 'review plan data was modified (if test = False)',
            401: 'current app user not authorized to modify review plan',
            404: 'no review with matching id was found',
            }
        )
    @use_args(ReviewPlanSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', required=True),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, fields, test):
        """modify review plan record for a single review by id"""
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to create this review plan'.format(g.current_user))
        review_plan = review.review_plan
        if not review_plan:
            return no_data_found('<ReviewPlan(review_id={})> not found'.format(id))
        for field in fields:
            try:
                setattr(review_plan, field, args[field])
            except KeyError:
                return validation('field "{}" value not specified'.format(field))
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return ReviewPlanSchema().dump(review_plan).data
