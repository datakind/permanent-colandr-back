from flask import Flask
from flask_restful import Api
from flask_restful_swagger import swagger
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .config import config
from .api.users import UserResource, UsersResource
from .api.reviews import ReviewResource, ReviewsResource
from .api.reviewplans import ReviewPlanResource, ReviewPlansResource
from .api.citations import CitationResource, CitationsResource
from .api.review_progress import ReviewProgressResource
from .api.authentication import AuthTokenResource


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)

    db.init_app(app)

    api = swagger.docs(
        Api(app),
        apiVersion='0.1',
        api_spec_url='/spec',
        description='Colandr API')

    api.add_resource(AuthTokenResource, '/authtoken')
    api.add_resource(UsersResource, '/users')
    api.add_resource(UserResource, '/users/<int:user_id>')
    api.add_resource(ReviewsResource, '/reviews')
    api.add_resource(ReviewResource, '/reviews/<int:review_id>')
    api.add_resource(ReviewProgressResource, '/reviews/<int:review_id>/progress')
    api.add_resource(ReviewPlansResource, '/reviewplans')
    api.add_resource(ReviewPlanResource, '/reviewplans/<int:reviewplan_id>')
    api.add_resource(CitationsResource, '/citations')
    api.add_resource(CitationResource, '/citations/<int:citation_id>')

    return app
