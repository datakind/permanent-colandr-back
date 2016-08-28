import logging

import flask
from flask import Flask, jsonify, make_response
from flask_httpauth import HTTPBasicAuth
from flask_restful import Api, Resource
from flask_restful_swagger import swagger

import ciapi
from ciapi.resources.citations import Citation, Citations
from ciapi.resources.reviews import Review, Reviews
from ciapi.resources.users import User
import cipy


USERS_DDL = cipy.db.db_utils.get_ddl('users')

errors = {
    'DataIntegrityError': {
        'message': 'Input data can not be inserted into the database.',
        'status': 409},
    'ValidationError': {
        'message': 'Input data does not pass type and value validation.',
        'status': 422},
    }


class MissingData(Exception):
    status_code = 404

    def __init__(self, message, status_code=None, payload=None):
        Exception.__init__(self)
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        self.payload = payload

    def to_dict(self):
        rv = dict(self.payload or ())
        rv['message'] = self.message
        return rv


app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'

# Logging
_logger = logging.getLogger('API')
_logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
app.logger.addHandler(_handler)

auth = HTTPBasicAuth()

# api = Api(app)
api = swagger.docs(
    Api(app, catch_all_404s=False, errors=errors),
    apiVersion='0.1',
    api_spec_url='/spec',
    description='Burton\'s First API!')


@app.errorhandler(422)
def handle_unprocessable_entity(err):
    # webargs attaches additional metadata to the `data` attribute
    data = getattr(err, 'data')
    if data:
        # Get validations from the ValidationError object
        messages = data['exc'].messages
    else:
        messages = ['Invalid request']
    return jsonify({'messages': messages}), 422


@auth.verify_password
def verify_user(email, password):
    db_matches = list(
        ciapi.PGDB.run_query(
            USERS_DDL['templates']['login_user'],
            bindings={'email': email, 'password': password}))
    if not db_matches:
        return False
    assert len(db_matches) == 1
    flask.session['user'] = db_matches[0]
    return True


@auth.error_handler
def unauthorized():
    return make_response(jsonify({'message': 'Unauthorized!'}))


class Login(Resource):
    @auth.login_required
    def get(self):
        return flask.session['user']


api.add_resource(Login, '/login')
api.add_resource(Citations, '/citations')
api.add_resource(Citation, '/citations/<int:citation_id>')
api.add_resource(Reviews, '/reviews')
api.add_resource(Review, '/reviews/<int:review_id>', '/reviews')
api.add_resource(User, '/users/<int:user_id>', '/users')


if __name__ == '__main__':
    app.run(debug=True)
