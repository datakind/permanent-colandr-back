from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..models import db, Review, ReviewPlan
from ..lib import constants
from .errors import unauthorized
from .schemas import ReviewPlanSchema
from .authentication import auth


class ReviewPlanResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'reviewplan_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, reviewplan_id, fields):
        review_plan = db.session.query(ReviewPlan).get(reviewplan_id)
        if not review_plan:
            raise NoResultFound
        if review_plan.review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review plan'.format(g.current_user))
        return ReviewPlanSchema(only=fields).dump(review_plan).data

    @swagger.operation()
    @use_kwargs({
        'reviewplan_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, reviewplan_id, test):
        review_plan = db.session.query(ReviewPlan).get(reviewplan_id)
        if not review_plan:
            raise NoResultFound
        if review_plan.review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to delete this review plan'.format(g.current_user))
        if test is False:
            db.session.delete(review_plan)
            db.session.commit()

    @swagger.operation()
    @use_args(ReviewPlanSchema(partial=True))
    @use_kwargs({
        'reviewplan_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, reviewplan_id, test):
        review_plan = db.session.query(ReviewPlan).get(reviewplan_id)
        if not review_plan:
            raise NoResultFound
        if review_plan.review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to update this review plan'.format(g.current_user))
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(review_plan, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return ReviewPlanSchema().dump(review_plan).data


class ReviewPlansResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, review_id, fields):
        review = db.sessionquery(Review).get(review_id)
        if not review:
            raise NoResultFound
        if review.collaborators.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review plan'.format(g.current_user))
        review_plan = review.review_plan
        return ReviewPlanSchema(only=fields).dump(review_plan).data

    @swagger.operation()
    @use_args(ReviewPlanSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        review = db.session.query(Review).get(args['review_id'])
        if not review:
            raise NoResultFound
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to create this review plan'.format(g.current_user))
        review_plan = ReviewPlan(**args)
        if test is False:
            review_plan.review = review
            db.session.add(review_plan)
            db.session.commit()
        return ReviewPlanSchema().dump(review_plan).data
