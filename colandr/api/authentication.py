from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth
from flask_restful import Resource

from ..models import db, User
from .errors import unauthorized


auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    # authenticate by token
    if not password:
        g.current_user = User.verify_auth_token(email_or_token)
        g.token_used = True
        return g.current_user is not None
    # authenticate by email + password
    else:
        user = db.session.query(User).filter_by(email=email_or_token).one_or_none()
        if not user:
            return False
        if user.is_confirmed is False:
            return False
        g.current_user = user
        g.token_used = False
        return user.verify_password(password)


@auth.error_handler
def auth_error():
    return unauthorized('invalid or expired authentication credentials')


class AuthTokenResource(Resource):

    @auth.login_required
    def get(self):
        if g.token_used is True:
            return unauthorized('invalid authentication credentials')
        token = g.current_user.generate_auth_token()
        return jsonify({'token': token})



# @api.before_request
# @auth.login_required
# def before_request():
#     if not g.current_user.is_anonymous and \
#             not g.current_user.confirmed:
#         return forbidden('Unconfirmed account')
#
#
# @api.route('/token')
# def get_token():
#     if g.current_user.is_anonymous or g.token_used:
#         return unauthorized('Invalid credentials')
#     return jsonify({'token': g.current_user.generate_auth_token(
#         expiration=3600), 'expiration': 3600})
