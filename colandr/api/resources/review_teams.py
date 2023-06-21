import flask_praetorian
from flask import g, current_app, render_template
from flask_restx import Namespace, Resource

from itsdangerous import URLSafeSerializer
from marshmallow import fields as ma_fields
from marshmallow.validate import OneOf, Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_kwargs

from ...lib import constants
from ...models import db, Review, User
from ...tasks import send_email
from ..errors import forbidden_error, not_found_error, validation_error
from ..schemas import UserSchema
from colandr import api


ns = Namespace(
    'review_teams', path='/reviews',
    description='get, modify, and confirm review teams')


@ns.route('/<int:id>/team')
@ns.doc(
    summary='get and modify review teams',
    produces=['application/json'],
    )
class ReviewTeamResource(Resource):

    method_decorators = [flask_praetorian.auth_required]

    @ns.doc(
        params={'fields': {'in': 'query', 'type': 'string',
                           'description': 'comma-delimited list-as-string of user fields to return'},
                },
        responses={
            200: 'successfully got review team member\'s records',
            403: 'current app user forbidden to get review team member\'s records',
            404: 'no review with matching id was found'}
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'fields': DelimitedList(
            ma_fields.String, delimiter=',', missing=None)
        })
    def get(self, id, fields):
        """get members of a single review's team"""
        review = db.session.query(Review).get(id)
        if not review:
            return not_found_error('<Review(id={})> not found'.format(id))
        if (g.current_user.is_admin is False and
                review.users.filter_by(id=g.current_user.id).one_or_none() is None):
            return forbidden_error(
                '{} forbidden to get this review'.format(g.current_user))
        if fields and 'id' not in fields:
            fields.append('id')
        users = UserSchema(many=True, only=fields).dump(review.users).data
        owner_user_id = review.owner_user_id
        for user in users:
            if user['id'] == owner_user_id:
                user['is_owner'] = True
        current_app.logger.debug('got %s team members for %s', len(users), review)
        return users

    @ns.doc(
        params={
            'action': {'in': 'query', 'type': 'string', 'required': True,
                       'enum': ['add', 'invite', 'remove', 'make_owner'],
                       'description': 'add, invite, remove, or promote to owner a particular user'},
            'user_id': {'in': 'query', 'type': 'integer', 'min': 1, 'max': constants.MAX_INT,
                        'description': 'unique id of the user on which to act'},
            'user_email': {'in': 'query', 'type': 'string', 'format': 'email',
                           'description': 'email address of the user to invite'},
            'server_name': {'in': 'query', 'type': 'string', 'default': None,
                            'description': 'name of server used to build confirmation url, e.g. "http://www.colandrapp.com"'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'successfully modified review team member\'s record',
            403: 'current app user forbidden to modify review team',
            404: 'no review with matching id was found'}
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'action': ma_fields.Str(
            required=True, validate=OneOf(['add', 'invite', 'remove', 'make_owner'])),
        'user_id': ma_fields.Int(
            missing=None, validate=Range(min=1, max=constants.MAX_INT)),
        'user_email': ma_fields.Email(missing=None),
        'server_name': ma_fields.Str(missing=None),
        'test': ma_fields.Bool(missing=False)
        })
    def put(self, id, action, user_id, user_email, server_name, test):
        """add, invite, remove, or promote a review team member"""
        review = db.session.query(Review).get(id)
        if not review:
            return not_found_error('<Review(id={})> not found'.format(id))
        if review.owner is not g.current_user:
            return forbidden_error(
                '{} forbidden to modify this review team'.format(g.current_user))
        if user_id is not None:
            user = db.session.query(User).get(user_id)
        elif user_email is not None:
            user = db.session.query(User).filter_by(email=user_email).one_or_none()
            if user is not None:
                user_id = user.id
        else:
            return validation_error('user_id or user_email is required')
        review_users = review.users
        # an existing user is being added, without an invite email
        if action == 'add':
            # TODO: should this be admins only?
            if user is None:
                return not_found_error('no user found with given id or email')
            elif user not in review_users:
                review_users.append(user)
            else:
                return forbidden_error(
                    '{} is already on this review'.format(user))
        # user is being *invited*, so send an invitation email
        elif action == 'invite':
            serializer = URLSafeSerializer(current_app.config['SECRET_KEY'])
            token = serializer.dumps(
                user_email, salt=current_app.config['PASSWORD_SALT'])
            if server_name:
                confirm_url = server_name + '{}/{}/team/confirm?token={}'.format(
                    ns.path, id, token)
            else:
                confirm_url = api.api_.url_for(
                    ConfirmReviewTeamInviteResource,
                    id=id, token=token, _external=True)
            # this user doesn't exist...
            if user is None:
                html = render_template(
                    'emails/invite_new_user_to_review.html',
                    url=confirm_url, inviter_email=g.current_user.email, review_name=review.name)
            # this user is already in our system
            else:
                html = render_template(
                    'emails/invite_user_to_review.html',
                    url=confirm_url, inviter_email=g.current_user.email, review_name=review.name)
            if test is False:
                send_email.apply_async(
                    args=[[user_email], "Let's collaborate!", '', html])
        elif action == 'make_owner':
            if user is None:
                return not_found_error('no user found with given id or email')
            review.owner_user_id = user_id
            review.owner = user
        elif action == 'remove':
            if user is None:
                return not_found_error('no user found with given id or email')
            if user_id == review.owner_user_id:
                return forbidden_error('current review owner can not be removed from team')
            if review_users.filter_by(id=user_id).one_or_none() is not None:
                review_users.remove(user)

        if test is False:
            db.session.commit()
            current_app.logger.info('for %s, %s %s', review, action, user)
        else:
            db.session.rollback()
        users = UserSchema(many=True).dump(review.users).data
        owner_user_id = review.owner_user_id
        for user in users:
            if user['id'] == owner_user_id:
                user['is_owner'] = True
        return users


@ns.route('/<int:id>/team/confirm')
@ns.doc(
    summary='confirm an emailed invitation to join a review team',
    produces=['application/json'],
    )
class ConfirmReviewTeamInviteResource(Resource):

    @ns.doc(
        params={
            'token': {'in': 'query', 'type': 'string', 'required': True,
                      'description': 'unique, expiring token included in emailed confirmation url'},
            },
        responses={
            200: 'successfully modified review team member\'s record',
            403: 'current app user\'s confirmation token is invalid or has expired',
            404: 'no review with matching id was found'}
        )
    @use_kwargs({
        'id': ma_fields.Int(
            required=True, location='view_args',
            validate=Range(min=1, max=constants.MAX_INT)),
        'token': ma_fields.String(required=True)
        })
    def get(self, id, token):
        """confirm review team invitation via emailed token"""
        serializer = URLSafeSerializer(current_app.config['SECRET_KEY'])
        user_email = serializer.loads(token, salt=current_app.config['PASSWORD_SALT'])

        review = db.session.query(Review).get(id)
        if not review:
            return not_found_error('<Review(id={})> not found'.format(id))
        review_users = review.users

        user = db.session.query(User).filter_by(email=user_email).one_or_none()
        if user is None:
            return forbidden_error('user not found')
        if user not in review_users:
            review_users.append(user)
        else:
            return forbidden_error('{} is already on this review'.format(user))

        db.session.commit()
        current_app.logger.info('invitation to %s confirmed by %s', review, user_email)
        users = UserSchema(many=True).dump(review.users).data
        owner_user_id = review.owner_user_id
        for user in users:
            if user['id'] == owner_user_id:
                user['is_owner'] = True
        return users
