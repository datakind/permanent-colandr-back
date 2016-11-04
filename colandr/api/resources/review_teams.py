from flask import g, current_app, render_template, url_for
from flask_restful import Resource
from flask_restful_swagger import swagger

from itsdangerous import URLSafeSerializer
from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from ...models import db, Review, User
from ...lib import constants
from ...tasks import send_email
from ..errors import forbidden, no_data_found, unauthorized, validation
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
            return no_data_found('<Review(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
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
        'action': ma_fields.Str(
            required=True, validate=OneOf(['add', 'invite', 'remove', 'make_owner'])),
        'user_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'user_email': ma_fields.Email(missing=None),
        'test': ma_fields.Bool(missing=False)
        })
    def put(self, id, action, user_id, user_email, test):
        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return unauthorized(
                '{} not authorized to modify this review team'.format(g.current_user))
        if user_id is not None:
            user = db.session.query(User).get(user_id)
        elif user_email is not None:
            user = db.session.query(User).filter_by(email=user_email).one_or_none()
        else:
            return validation('user_id or user_email is required')
        review_users = review.users
        # an existing user is being added, without an invite email
        if action == 'add':
            if user is None:
                return forbidden('<User(id={})> not found'.format(user_id))
            elif user not in review_users:
                review_users.append(user)
            else:
                return forbidden(
                    '{} is already on this review'.format(user))
        # user is being *invited*, so send an invitation email
        elif action == 'invite':
            serializer = URLSafeSerializer(current_app.config['SECRET_KEY'])
            token = serializer.dumps(
                user_email, salt=current_app.config['PASSWORD_SALT'])
            url = url_for(
                'confirmreviewteaminviteresource',
                id=id, token=token, _external=True)
            html = render_template(
                'emails/invite_user_to_review.html',
                url=url, inviter_email=g.current_user.email, review_name=review.name)
            if test is False:
                send_email.apply_async(
                    args=[[user_email], "Let's collaborate!", '', html])
        elif action == 'make_owner':
            review.owner_user_id = user_id
            review.owner = user
        elif action == 'remove':
            if user_id == review.owner_user_id:
                return forbidden('current review owner can not be removed from team')
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


class ConfirmReviewTeamInviteResource(Resource):

    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'token': ma_fields.String(required=True)
        })
    def get(self, id, token):
        serializer = URLSafeSerializer(current_app.config['SECRET_KEY'])
        user_email = serializer.loads(token, salt=current_app.config['PASSWORD_SALT'])

        review = db.session.query(Review).get(id)
        if not review:
            return no_data_found('<Review(id={})> not found'.format(id))
        review_users = review.users

        user = db.session.query(User).filter_by(email=user_email).one_or_none()
        if user is None:
            return forbidden('user not found')
        if user not in review_users:
            review_users.append(user)
        else:
            return forbidden(
                '{} is already on this review'.format(user))

        db.session.commit()
        users = UserSchema(many=True).dump(review.users).data
        owner_user_id = review.owner_user_id
        for user in users:
            if user['id'] == owner_user_id:
                user['is_owner'] = True
        return users
