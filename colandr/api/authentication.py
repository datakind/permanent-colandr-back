import flask
from flask import jsonify
from flask_httpauth import HTTPBasicAuth
from flask_restful import Resource

from ..models import db, User
from .schemas import UserSchema
from .errors import unauthorized  # , forbidden


auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    # try to authenticate by token
    if not password:
        user = User.verify_auth_token(email_or_token)
    # try to authenticate with email + password
    else:
        user = db.session.query(User).filter_by(email=email_or_token).one_or_none()
        if not user or not user.verify_password(password):
            return False
    flask.session['user'] = UserSchema().dump(user).data
    return True


@auth.error_handler
def auth_error():
    return unauthorized('invalid authentication credentials')


class AuthTokenResource(Resource):

    @auth.login_required
    def get(self):
        current_user = db.session.query(User).get(flask.session['user']['id'])
        token = current_user.generate_auth_token()
        return jsonify({'token': token.decode('ascii')})



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
