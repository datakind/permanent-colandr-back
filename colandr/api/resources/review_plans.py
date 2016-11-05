from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, utils
from ...models import db, Review
from ..errors import no_data_found, unauthorized, validation
from ..schemas import ReviewPlanSchema
from ..authentication import auth


logger = utils.get_console_logger(__name__)


class ReviewPlanResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
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

    # NOTE: since review plans are created automatically upon review insertion
    # and deleted automatically upon review deletion, "delete" here amounts
    # to nulling out some or all of its non-required fields
    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, fields, test):
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
        else:
            db.session.rollback()
        return '', 204

    @swagger.operation()
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
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to create this review plan'.format(g.current_user))
        review_plan = review.review_plan
        if not review_plan:
            return no_data_found('<ReviewPlan(review_id={})> not found'.format(id))
        if review_plan.review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to update this review plan'.format(g.current_user))
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
