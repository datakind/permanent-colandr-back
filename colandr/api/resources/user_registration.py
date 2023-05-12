from flask import current_app, render_template  # , url_for
from flask_restx import Resource
from sqlalchemy.exc import IntegrityError, InvalidRequestError

from marshmallow import fields as ma_fields
from webargs.flaskparser import use_args, use_kwargs

from ...models import db, User
from ...tasks import remove_unconfirmed_user, send_email
from ..errors import db_integrity_error, not_found_error, validation_error
from ..registration import confirm_token, generate_confirmation_token
from ..schemas import UserSchema
from ..swagger import user_model
from colandr import api_


ns = api_.namespace(
    'user registration', path='/register',
    description='register and confirm new users')


@ns.route('')
class UserRegistrationResource(Resource):

    @ns.doc(
        params={
            'server_name': {'in': 'query', 'type': 'string', 'default': None,
                            'description': 'name of server used to build confirmation url, e.g. "http://www.colandrapp.com"'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'}
            },
        body=(user_model, 'user data to be registered'),
        )
    @use_args(UserSchema())
    @use_kwargs({
        'server_name': ma_fields.Str(missing=None),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, args, server_name, test):
        """submit new user registration"""
        user = User(**args)
        token = generate_confirmation_token(user.email)
        if server_name:
            confirm_url = server_name + '{}/{}'.format(ns.path, token)
        else:
            confirm_url = api_.url_for(
                ConfirmUserRegistrationResource, token=token, _external=True)
        html = render_template(
            'emails/user_registration.html',
            username=user.name, confirm_url=confirm_url)
        if test is False:
            try:
                db.session.add(user)
                db.session.commit()
            except (IntegrityError, InvalidRequestError) as e:
                db.session.rollback()
                return db_integrity_error(str(e.orig))
            send_email.apply_async(
                args=[[user.email], 'Confirm your email', '', html])
            remove_unconfirmed_user.apply_async(
                args=[user.email],
                countdown=current_app.config['CONFIRM_TOKEN_EXPIRATION'])
            current_app.logger.info('user registration email sent to %s', user.email)
        return UserSchema().dump(user).data


@ns.route('/<token>')
class ConfirmUserRegistrationResource(Resource):

    @use_kwargs({'token': ma_fields.String(required=True, location='view_args')})
    def get(self, token):
        """confirm new user registration via emailed token"""
        try:
            email = confirm_token(token)
        except Exception:
            return validation_error('the confirmation link is invalid or has expired')
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if not user:
            return not_found_error("sorry! we couldn't find you in our database")
        if user.is_confirmed is True:
            return validation_error('user already confirmed! please login')
        user.is_confirmed = True
        db.session.commit()
        current_app.logger.info('user registration confirmed by %s', email)
