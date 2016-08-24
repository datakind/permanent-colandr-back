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


app = Flask(__name__)
app.config['SECRET_KEY'] = 'the quick brown fox jumps over the lazy dog'
auth = HTTPBasicAuth()

# api = Api(app)
api = swagger.docs(
    Api(app),
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


class Root(Resource):
    @auth.login_required
    def get(self):
        return flask.session['user']


api.add_resource(Root, '/')
api.add_resource(Citations, '/citations')
api.add_resource(Citation, '/citations/<int:citation_id>')
api.add_resource(Reviews, '/reviews')
api.add_resource(Review, '/reviews/<int:review_id>')
api.add_resource(User, '/users/<int:user_id>', '/users')


if __name__ == '__main__':
    app.run(debug=True)
