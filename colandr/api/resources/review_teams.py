from flask import g
from flask_restful import Resource
from flask_restful_swagger import swagger
from sqlalchemy.orm.exc import NoResultFound

from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from ...models import db, Review, User
from ...lib import constants
from ..errors import forbidden, unauthorized
from ..schemas import UserSchema
from ..authentication import auth


class ReviewTeamResource(Resource):

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
            raise NoResultFound
        if review.users.filter_by(id=g.current_user.id).one_or_none() is None:
            return unauthorized(
                '{} not authorized to get this review'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        users = UserSchema(many=True, only=fields).dump(review.users).data
        owner_user_id = review.owner_user_id
        for user in users:
            if user['id'] == owner_user_id:
                user['is_owner'] = True
        return users

    @swagger.operation()
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'user_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'action': ma_fields.Str(
            required=True, validate=OneOf(['add', 'remove', 'make_owner'])),
        'test': ma_fields.Bool(missing=False)
        })
    def put(self, id, user_id, action, test):
        review = db.session.query(Review).get(id)
        if not review:
            raise NoResultFound
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to modify this review team'.format(g.current_user))
        user = db.session.query(User).get(user_id)
        if action == 'make_owner':
            review.owner_user_id = user_id
            review.owner = user
        review_users = review.users
        if action == 'add':
            if review_users.filter_by(id=user_id).one_or_none() is None:
                review_users.append(user)
        elif action == 'remove':
            if user_id == review.owner_user_id:
                raise forbidden('current review owner can not be removed from team')
            if review_users.filter_by(id=user_id).one_or_none() is not None:
                review_users.remove(user)
        if test is False:
            db.session.commit()
        else:
            db.session.rollback()
        users = UserSchema(many=True).dump(review.users).data
        owner_user_id = review.owner_user_id
        for user in users:
            if user['id'] == owner_user_id:
                user['is_owner'] = True
        return users
