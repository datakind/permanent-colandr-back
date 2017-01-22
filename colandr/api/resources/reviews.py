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
from ..swagger import review_model
from ..authentication import auth
from colandr import api_

logger = utils.get_console_logger(__name__)
ns = api_.namespace(
    'reviews', path='/reviews',
    description='get, create, delete, update reviews')


@ns.route('/<int:id>')
@ns.doc(
    summary='get, delete, and modify data for single reviews',
    produces=['application/json'],
    )
class ReviewResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        params={'fields': {'in': 'query', 'type': 'string',
                           'description': 'comma-delimited list-as-string of review fields to return'},
                },
        responses={
            200: 'successfully got review record',
            401: 'current app user not authorized to get review record',
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
        """get record for a single review by id"""
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

    @ns.doc(
        params={'test': {'in': 'query', 'type': 'boolean', 'default': False,
                         'description': 'if True, request will be validated but no data will be affected'},
                },
        responses={
            200: 'request was valid, but record not deleted because `test=False`',
            204: 'successfully deleted review record',
            401: 'current app user not authorized to delete review record',
            404: 'no review with matching id was found'
            }
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def delete(self, id, test):
        """delete record for a single review by id"""
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to delete this review'.format(g.current_user))
        db.session.delete(review)
        if test is False:
            db.session.commit()
            logger.info('deleted %s', review)
            return '', 204
        else:
            db.session.rollback()
            return '', 200

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        body=(review_model, 'review data to be modified'),
        responses={
            200: 'review data was modified (if test = False)',
            401: 'current app user not authorized to modify review',
            404: 'no review with matching id was found',
            }
        )
    @use_args(ReviewSchema(partial=True))
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'test': ma_fields.Boolean(missing=False)
        })
    def put(self, args, id, test):
        """modify record for a single review by id"""
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


@ns.route('')
@ns.doc(
    summary='get existing and create new reviews',
    produces=['application/json'],
    )
class ReviewsResource(Resource):

    method_decorators = [auth.login_required]

    @ns.doc(
        params={'fields': {'in': 'query', 'type': 'string',
                           'description': 'comma-delimited list-as-string of review fields to return'},
                },
        responses={200: 'successfully got review record(s)'}
        )
    @use_kwargs({
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, fields):
        """get all reviews on which current app user is a collaborator"""
        reviews = g.current_user.reviews.order_by(Review.id).all()
        if fields and 'id' not in fields:
            fields.append('id')
        return ReviewSchema(only=fields, many=True).dump(reviews).data

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        body=(review_model, 'review data to be created'),
        responses={
            200: 'review was created (or would have been created if test had been False)'
            }
        )
    @use_args(ReviewSchema(partial=['owner_user_id']))
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        """create new review"""
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
