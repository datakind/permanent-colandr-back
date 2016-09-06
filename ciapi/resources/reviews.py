import flask
from flask_restful import Resource  # , abort
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ciapi.models import db, Review, User
from ciapi.schemas import ReviewSchema
from ciapi.auth import auth


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
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if (review.owner_user is current_user or
                review.users.filter_by(id=current_user.id).one_or_none() is not None):
            if fields:
                return ReviewSchema(only=fields).dump(review).data
            else:
                return ReviewSchema().dump(review).data
        else:
            raise Exception('user not authorized to get this review')

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
        current_user = db.session.query(User).get(flask.session['user']['id'])
        if review.owner_user is not current_user:
            raise Exception(
                '{} not authorized to delete this review'.format(current_user))
        if test is False:
            db.session.delete(review)
            db.session.commit()


class ReviewsResource(Resource):

    method_decorators = [auth.login_required]

    @swagger.operation()
    @use_kwargs({
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, fields):
        owner_user_id = flask.session['user']['id']
        user = db.session.query(User).get(owner_user_id)
        owned_reviews = user.owned_reviews.order_by(Review.id).all()
        if fields:
            return ReviewSchema(only=fields, many=True).dump(owned_reviews).data
        else:
            return ReviewSchema(many=True).dump(owned_reviews).data

    @swagger.operation()
    @use_args(ReviewSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        args['owner_user_id'] = flask.session['user']['id']
        name = args.pop('name')
        review = Review(name, **args)
        if test is False:
            db.session.add(review)
            db.session.commit()
        return ReviewSchema().dump(review).data



# class Review(Resource):
#
#
#     @swagger.operation()
#     @use_args(ReviewSchema(only=['name', 'description', 'settings']))
#     @use_kwargs({'test': fields.Boolean(missing=False)})
#     def post(self, args, test):
#         args['owner_user_id'] = session['user']['user_id']
#         args['user_ids'] = [session['user']['user_id']]
#         args['settings'] = json.dumps(args['settings'])
#         if test is True:
#             list(PGDB.run_query(
#                 REVIEWS_DDL['templates']['create_review'],
#                 bindings=args,
#                 act=False))
#             return args
#         else:
#             created_review_id = list(PGDB.run_query(
#                 REVIEWS_DDL['templates']['create_review'],
#                 bindings=args,
#                 act=True))[0]['review_id']
#             return created_review_id
