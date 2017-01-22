from flask import render_template  # , url_for
from flask_restplus import Resource

from marshmallow import fields as ma_fields
from marshmallow.validate import Email
from webargs.flaskparser import use_kwargs

from ...lib import utils
from ...models import db, User
from ...tasks import send_email
from ..errors import forbidden, no_data_found, validation
from ..registration import confirm_token, generate_confirmation_token
from colandr import api_


logger = utils.get_console_logger(__name__)
ns = api_.namespace(
    'password reset', path='/reset',
    description='reset a user\'s password')


@ns.route('')
@ns.doc(
    summary='reset a user\'s password by sending an email',
    produces=['application/json'],
    )
class PasswordResetResource(Resource):

    @ns.doc(
        params={
            'email': {'in': 'query', 'type': 'string', 'required': True,
                      'description': 'email of user whose password is to be reset'},
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'},
            },
        responses={
            200: 'user was created (or would have been created if test had been False)',
            401: 'current app user not authorized to create user',
            }
        )
    @use_kwargs({
        'email': ma_fields.Str(
            required=True, validate=Email()),
        'test': ma_fields.Boolean(missing=False)
        })
    def post(self, email, test):
        """reset user's password"""
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if user is None:
            html = render_template(
                'emails/password_reset_invalid_email.html',
                email=email)
            if test is False:
                send_email.apply_async(
                    args=[[email], 'Reset Password?', '', html])
        else:
            token = generate_confirmation_token(user.email)
            # confirm_url = url_for(
            #     'confirmpasswordresetresource', token=token, _external=True)
            confirm_url = api_.url_for(
                ConfirmPasswordResetResource, token=token, _external=True)
            html = render_template(
                'emails/password_reset.html',
                username=user.name, confirm_url=confirm_url)
            if test is False:
                send_email.apply_async(
                    args=[[email], 'Reset Password', '', html])
                logger.info('password reset email sent to %s', email)


@ns.route('/<token>')
@ns.doc(
    summary='confirm a user\'s password reset via emailed token',
    produces=['application/json'],
    )
class ConfirmPasswordResetResource(Resource):

    @ns.doc(
        responses={
            200: 'password reset successfully confirmed',
            422: 'invalid or expired password reset link',
            }
        )
    @use_kwargs({'token': ma_fields.String(required=True, location='view_args')})
    def get(self, token):
        """confirm a user's password reset via emailed token"""
        try:
            email = confirm_token(token)
        except Exception:
            return validation('the password reset link is invalid or has expired')
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if not user:
            return no_data_found("sorry! we couldn't find you in our database")
        if user.is_confirmed is False:
            return forbidden('user not confirmed! please first confirm your email address.')
        # TODO: now what???
        logger.info('password reset confirmed by %s', email)
