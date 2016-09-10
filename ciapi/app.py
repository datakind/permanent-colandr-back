# import logging
import os

import flask
from flask import Flask, jsonify  # session, make_response
from flask_restful import Api, Resource
from flask_restful_swagger import swagger

import ciapi
from ciapi.resources.users import UserResource, UsersResource
from ciapi.resources.reviews import ReviewResource, ReviewsResource
from ciapi.resources.reviewplans import ReviewPlanResource, ReviewPlansResource
from ciapi.models import db, User
from ciapi.auth import auth


app = Flask(__name__)
app.config.from_object('ciapi.config')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ['SQLALCHEMY_DATABASE_URI']
app.config['SECRET_KEY'] = os.environ['COLANDR_SECRET_KEY']

db.init_app(app)

# api = Api(app)
api = swagger.docs(
    Api(app, catch_all_404s=False),  # , errors=errors),
    apiVersion='0.1',
    api_spec_url='/spec',
    description='Burton\'s First API!')


# Logging
# _logger = logging.getLogger('API')
# _logger.setLevel(logging.INFO)
# _handler = logging.StreamHandler()
# _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
# _handler.setFormatter(_formatter)
# app.logger.addHandler(_handler)


# errors = {
#     'DataIntegrityError': {
#         'message': 'Input data can not be inserted into the database.',
#         'status': 409},
#     'ValidationError': {
#         'message': 'Input data does not pass type and value validation.',
#         'status': 422},
#     }
#
#
# class MissingData(Exception):
#     status_code = 404
#
#     def __init__(self, message, status_code=None, payload=None):
#         Exception.__init__(self)
#         self.message = message
#         if status_code is not None:
#             self.status_code = status_code
#         self.payload = payload
#
#     def to_dict(self):
#         rv = dict(self.payload or ())
#         rv['message'] = self.message
#         return rv
#
#
# @app.errorhandler(422)
# def handle_unprocessable_entity(err):
#     # webargs attaches additional metadata to the `data` attribute
#     data = getattr(err, 'data')
#     if data:
#         # Get validations from the ValidationError object
#         messages = data['exc'].messages
#     else:
#         messages = ['Invalid request']
#     return jsonify({'messages': messages}), 422


class AuthTokenResource(Resource):

    @auth.login_required
    def get(self):
        current_user = db.session.query(User).get(flask.session['user']['id'])
        token = current_user.generate_auth_token()
        return jsonify({'token': token.decode('ascii')})


api.add_resource(AuthTokenResource, '/authtoken')
api.add_resource(UsersResource, '/users')
api.add_resource(UserResource, '/users/<int:user_id>')
api.add_resource(ReviewsResource, '/reviews')
api.add_resource(ReviewResource, '/reviews/<int:review_id>')
api.add_resource(ReviewPlansResource, '/reviewplans')
api.add_resource(ReviewPlanResource, '/reviewplans/<int:reviewplan_id>')

if __name__ == '__main__':
    app.run(debug=True)
