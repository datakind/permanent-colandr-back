from flask import g
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs import missing
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...lib import constants, utils
from ...models import db, Review
from ..errors import no_data_found, unauthorized
from ..schemas import ReviewSchema
from ..authentication import auth


logger = utils.get_console_logger(__name__)


class ReviewResource(Resource):

    method_decorators = [auth.login_required]

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
                '{} not authorized to get this review'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        return ReviewSchema(only=fields).dump(review).data

    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to delete this review'.format(g.current_user))
        if test is False:
            db.session.delete(review)
            db.session.commit()
            logger.info('deleted %s', review)
            return '', 204

    @use_args(ReviewSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
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

    @use_kwargs({
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, fields):
        reviews = g.current_user.reviews.order_by(Review.id).all()
        if fields and 'id' not in fields:
            fields.append('id')
        return ReviewSchema(only=fields, many=True).dump(reviews).data

    @use_args(ReviewSchema(partial=['owner_user_id']))
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        name = args.pop('name')
        review = Review(name, g.current_user.id, **args)
        g.current_user.owned_reviews.append(review)
        g.current_user.reviews.append(review)
        db.session.add(review)
        if test is False:
            db.session.commit()
            logger.info('inserted %s', review)
        else:
            db.session.rollback()
        return ReviewSchema().dump(review).data
