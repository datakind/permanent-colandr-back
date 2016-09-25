import os

from flask import Flask, send_from_directory
from flask_restful import Api
from flask_restful_swagger import swagger
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

from .config import config
from .api.errors import no_data_found
from .api.users import UserResource, UsersResource
from .api.reviews import ReviewResource, ReviewsResource
from .api.review_plans import ReviewPlanResource
from .api.review_teams import ReviewTeamResource
from .api.review_progress import ReviewProgressResource
from .api.citations import CitationResource, CitationsResource
from .api.citation_screenings import CitationScreeningsResource, CitationsScreeningsResource
from .api.fulltexts import FulltextResource, FulltextsResource
from .api.fulltext_screenings import FulltextScreeningsResource, FulltextsScreeningsResource
from .api.fulltext_uploads import FulltextUploadResource
from .api.authentication import AuthTokenResource


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    os.makedirs(config[config_name].FULLTEXT_UPLOAD_FOLDER, exist_ok=True)

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
    api.add_resource(FulltextsResource, '/fulltexts')
    api.add_resource(FulltextResource, '/fulltexts/<int:id>')
    api.add_resource(FulltextsScreeningsResource, '/fulltexts/screenings')
    api.add_resource(FulltextScreeningsResource, '/fulltexts/<int:id>/screenings')
    api.add_resource(FulltextUploadResource, '/fulltexts/<int:id>/upload')

    @app.route('/fulltexts/<id>/upload', methods=['GET'])
    def get_uploaded_fulltext_file(id):
        filename = None
        upload_dir = app.config['FULLTEXT_UPLOAD_FOLDER']
        for ext in app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
            fname = '{}{}'.format(id, ext)
            if os.path.isfile(os.path.join(upload_dir, fname)):
                filename = fname
                break
        if not filename:
            return no_data_found(
                'no uploaded file for <Fulltext(id={})> found'.format(id))
        return send_from_directory(upload_dir, filename)

    return app
