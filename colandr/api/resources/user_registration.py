from flask import current_app, render_template, url_for
from flask_restful import Resource
from sqlalchemy import exc

from marshmallow import fields as ma_fields
from webargs.flaskparser import use_args, use_kwargs

from ...models import db, User
from ...tasks import remove_unconfirmed_user, send_email
from ..errors import db_integrity, no_data_found, validation
from ..registration import confirm_token, generate_confirmation_token
from ..schemas import UserSchema


class RegisterUserResource(Resource):

    @use_args(UserSchema())
    @use_kwargs({'test': ma_fields.Boolean(missing=False)})
    def post(self, args, test):
        user = User(**args)
        if test is False:
            try:
                db.session.add(user)
                db.session.commit()
            except exc.IntegrityError as e:
                db.session.rollback()
                return db_integrity(str(e.orig))
            token = generate_confirmation_token(user.email)
            confirm_url = url_for('confirmuserresource', token=token, _external=True)
            html = render_template(
                'emails/user_confirmation.html', confirm_url=confirm_url)
            send_email.apply_async(
                args=[[user.email], 'Confirm your email', '', html])
            remove_unconfirmed_user.apply_async(
                args=[user.email],
                countdown=current_app.config['CONFIRM_TOKEN_EXPIRATION'])
        return UserSchema().dump(user).data


class ConfirmUserResource(Resource):

    @use_kwargs({'token': ma_fields.String(required=True)})
    def get(self, token):
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
