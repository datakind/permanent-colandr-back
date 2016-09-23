from flask import Flask
from flask_restful import Api
from flask_restful_swagger import swagger
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .config import config
from .api.users import UserResource, UsersResource
from .api.reviews import ReviewResource, ReviewsResource
from .api.review_plans import ReviewPlanResource
from .api.review_teams import ReviewTeamResource
from .api.review_progress import ReviewProgressResource
from .api.citations import CitationResource, CitationsResource
from .api.citation_screenings import CitationScreeningsResource, CitationsScreeningsResource
from .api.fulltext_screenings import FulltextScreeningsResource, FulltextsScreeningsResource
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
    api.add_resource(UserResource, '/users/<int:id>')
    api.add_resource(ReviewsResource, '/reviews')
    api.add_resource(ReviewResource, '/reviews/<int:id>')
    api.add_resource(ReviewTeamResource, '/reviews/<int:id>/team')
    api.add_resource(ReviewProgressResource, '/reviews/<int:id>/progress')
    api.add_resource(ReviewPlanResource, '/reviews/<int:id>/plan')
    api.add_resource(CitationsResource, '/citations')
    api.add_resource(CitationResource, '/citations/<int:id>')
    api.add_resource(CitationsScreeningsResource, '/citations/screenings')
    api.add_resource(CitationScreeningsResource, '/citations/<int:id>/screenings')
    api.add_resource(FulltextsScreeningsResource, '/fulltexts/screenings')
    api.add_resource(FulltextScreeningsResource, '/fulltexts/<int:id>/screenings')

    return app
