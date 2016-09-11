from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ..models import db, Review
from .errors import unauthorized
from .schemas import ReviewSchema
from .authentication import auth


class ReviewResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, review_id, fields):
        review = db.session.query(Review).get(review_id)
        if not review:
            raise NoResultFound
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))
        return ReviewSchema(only=fields).dump(review).data

    @swagger.operation()
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, review_id, test):
        review = db.session.query(Review).get(review_id)
        if not review:
            raise NoResultFound
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to delete this review'.format(g.current_user))
        if test is False:
            db.session.delete(review)
            db.session.commit()

    @swagger.operation()
    @use_args(ReviewSchema(partial=True))
    @use_kwargs({
        'review_id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=2147483647)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, review_id, test):
        review = db.session.query(Review).get(review_id)
        if not review:
            raise NoResultFound
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to update this review'.format(g.current_user))
        for key, value in args.items():
            if key is missing:
                continue
            else:
                setattr(review, key, value)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        return ReviewSchema().dump(review).data


class ReviewsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, fields):
        reviews = g.current_user.reviews.order_by(Review.id).all()
        return ReviewSchema(only=fields, many=True).dump(reviews).data

    @swagger.operation()
    @use_args(ReviewSchema(partial=['owner_user_id']))
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        name = args.pop('name')
        review = Review(name, g.current_user.id, **args)
        if test is False:
            g.current_user.owned_reviews.append(review)
            g.current_user.reviews.append(review)
            db.session.add(review)
            db.session.commit()
        return ReviewSchema().dump(review).data
