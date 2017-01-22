from flask import current_app, render_template  # , url_for
from flask_restplus import Resource
from sqlalchemy import exc

from marshmallow import fields as ma_fields
from webargs.flaskparser import use_args, use_kwargs

from ...lib import utils
from ...models import db, User
from ...tasks import remove_unconfirmed_user, send_email
from ..errors import db_integrity, no_data_found, validation
from ..registration import confirm_token, generate_confirmation_token
from ..schemas import UserSchema
from ..swagger import user_model
from colandr import api_


logger = utils.get_console_logger(__name__)
ns = api_.namespace(
    'user registration', path='/register',
    description='register and confirm new users')


@ns.route('')
class UserRegistrationResource(Resource):

    @ns.doc(
        params={
            'test': {'in': 'query', 'type': 'boolean', 'default': False,
                     'description': 'if True, request will be validated but no data will be affected'}
            },
        body=(user_model, 'user data to be registered'),
        )
    @use_args(UserSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        """submit new user registration"""
        user = User(**args)
        if test is False:
            try:
                db.session.add(user)
                db.session.commit()
            except exc.IntegrityError as e:
                db.session.rollback()
                return db_integrity(str(e.orig))
            token = generate_confirmation_token(user.email)
            # confirm_url = url_for(
            #     'confirmuserregistrationresource', token=token, _external=True)
            confirm_url = api_.url_for(
                ConfirmUserRegistrationResource, token=token, _external=True)
            html = render_template(
                'emails/user_registration.html',
                username=user.name, confirm_url=confirm_url)
            send_email.apply_async(
                args=[[user.email], 'Confirm your email', '', html])
            remove_unconfirmed_user.apply_async(
                args=[user.email],
                countdown=current_app.config['CONFIRM_TOKEN_EXPIRATION'])
            logger.info('user registration email sent to %s', user.email)
        return UserSchema().dump(user).data


@ns.route('/<token>')
class ConfirmUserRegistrationResource(Resource):

    @use_kwargs({'token': ma_fields.String(required=True, location='view_args')})
    def get(self, token):
        """confirm new user registration via emailed token"""
        try:
            email = confirm_token(token)
        except Exception:
            return validation('the confirmation link is invalid or has expired')
        user = db.session.query(User).filter_by(email=email).one_or_none()
        if not user:
            return no_data_found("sorry! we couldn't find you in our database")
        if user.is_confirmed is True:
            return validation('user already confirmed! please login')
        user.is_confirmed = True
        db.session.commit()
        logger.info('user registration confirmed by %s', email)
