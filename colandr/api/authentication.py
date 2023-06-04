import os

from flask import g, jsonify
from flask_httpauth import HTTPBasicAuth, HTTPTokenAuth, MultiAuth
from flask_restx import Namespace, Resource
from itsdangerous import BadSignature, SignatureExpired, TimedJSONWebSignatureSerializer

from ..extensions import db
from ..models import User
from .errors import unauthorized_error


ns = Namespace(
    'authtoken', path='/authtoken',
    description='get an api authentication token')

jws = TimedJSONWebSignatureSerializer(os.environ["COLANDR_SECRET_KEY"], expires_in=3600)
basic_auth = HTTPBasicAuth()
token_auth = HTTPTokenAuth()
auth = MultiAuth(basic_auth, token_auth)


@basic_auth.verify_password
def verify_password_v2(email, password):
    user = db.session.query(User).filter_by(email=email).one_or_none()
    if user is None or user.is_confirmed is False:
        return None
    g.current_user = user
    # g.token_used = False  # TODO: what's this for
    return user.verify_password(password)


@token_auth.verify_token
def verify_token(token):
    try:
        data = jws.loads(token)
    except (BadSignature, SignatureExpired):
        return None

    user = db.session.query(User).one_or_none(data["id"])
    g.current_user = user
    # g.token_used = True
    return user


@basic_auth.error_handler
def auth_error():
    return unauthorized_error('invalid or expired authentication credentials')


@ns.route('')
@ns.doc(
    summary='get an api authentication token',
    produces=['application/json'],
    responses={200: 'successfully got authentication token',
               401: 'current app user not authorized to get authentication token',
               }
    )
class AuthTokenResource(Resource):

    @auth.login_required
    def get(self):
        """get an api authentication token"""
        # if g.token_used is True:
        #     return unauthorized('invalid authentication credentials')
        token = g.current_user.generate_auth_token()
        return jsonify({'token': token})
