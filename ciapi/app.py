from flask import Flask
from flask_restful import Api

from ciapi.resources.citations import Citation, Citations
from ciapi.resources.users import User, NewUser


app = Flask(__name__)
api = Api(app)

api.add_resource(Citations, '/citations')
api.add_resource(Citation, '/citations/<int:citation_id>')
api.add_resource(User, '/users/<int:user_id>')
api.add_resource(NewUser, '/users/register')


if __name__ == '__main__':
    app.run(debug=True)
