from flask import Flask
from flask_restful import Api

from ciapi.resources.citations import Citation  # Citations


APP = Flask(__name__)
API = Api(APP)

# API.add_resource(Citations, '/citations')
API.add_resource(Citation, '/citations/<int:citation_id>')


if __name__ == '__main__':
    APP.run(debug=True)
