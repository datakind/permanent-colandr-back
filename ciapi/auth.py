import flask
from flask_httpauth import HTTPBasicAuth

from ciapi.models import db, User
from ciapi.schemas import UserSchema

# authentication
auth = HTTPBasicAuth()


@auth.verify_password
def verify_password(email_or_token, password):
    # try to authenticate by token
    user = User.verify_auth_token(email_or_token)
    if not user:
        # try to authenticate with email + password
        user = db.session.query(User).filter_by(email=email_or_token).one_or_none()
        if not user or not user.verify_password(password):
            return False
    flask.session['user'] = UserSchema().dump(user).data
    return True


# @auth.error_handler
# def unauthorized():
#     return make_response(jsonify({'message': 'Unauthorized!'}))
