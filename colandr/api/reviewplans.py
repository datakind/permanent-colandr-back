import flask
from flask_restful import Resource  # , abort
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..models import db, Review, ReviewPlan, User
from .schemas import ReviewPlanSchema
from .authentication import auth


class ReviewPlanResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'reviewplan_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, reviewplan_id, fields):
        reviewplan = db.session.query(ReviewPlan).get(reviewplan_id)
        if not reviewplan:
            raise NoResultFound
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if reviewplan.review.collaborators.filter_by(id=current_user.id).one_or_none() is None:
            raise Exception(
                '{} not authorized to get this review'.format(current_user))
        return ReviewPlanSchema(only=fields).dump(reviewplan).data

    @swagger.operation()
    @use_kwargs({
        'reviewplan_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, reviewplan_id, test):
        reviewplan = db.session.query(ReviewPlan).get(reviewplan_id)
        if not reviewplan:
            raise NoResultFound
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if reviewplan.review.owner is not current_user:
            raise Exception(
                '{} not authorized to delete this review plan'.format(current_user))
        if test is False:
            db.session.delete(reviewplan)
            db.session.commit()

    @swagger.operation()
    @use_args(ReviewPlanSchema(partial=True))
    @use_kwargs({
        'reviewplan_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, reviewplan_id, test):
        reviewplan = db.session.query(ReviewPlan).get(reviewplan_id)
        if not reviewplan:
            raise NoResultFound
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if reviewplan.review.owner is not current_user:
            raise Exception(
                '{} not authorized to update this review plan'.format(current_user))
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(reviewplan, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return ReviewPlanSchema().dump(reviewplan).data


class ReviewPlansResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, review_id, fields):
        review = db.sessionquery(Review).get(review_id)
        if not review:
            raise NoResultFound
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if review.collaborators.filter_by(id=current_user.id).one_or_none() is None:
            raise Exception(
                '{} not authorized to get this review plan'.format(current_user))
        reviewplan = review.review_plan
        return ReviewPlanSchema(only=fields).dump(reviewplan).data

    @swagger.operation()
    @use_args(ReviewPlanSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        review = db.session.query(Review).get(args['review_id'])
        if not review:
            raise NoResultFound
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if review.owner is not current_user:
            raise Exception(
                '{} not authorized to create this review plan'.format(current_user))
        reviewplan = ReviewPlan(**args)
        if test is False:
            reviewplan.review = review
            db.session.add(reviewplan)
            db.session.commit()
        return ReviewPlanSchema().dump(reviewplan).data
