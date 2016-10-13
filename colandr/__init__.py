import os

from celery import Celery
from flask import Flask, jsonify, send_from_directory
# from flask_restful import Api
# from flask_restful_swagger import swagger
from flask_mail import Mail
from flask_migrate import Migrate  # check
from flask_restful_swagger_2 import Api
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
mail = Mail()
migrate = Migrate()

from .config import config, Config

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

from .api.authentication import AuthTokenResource
from .api.errors import no_data_found
from .api.resources.users import UserResource, UsersResource
from .api.resources.user_registration import ConfirmUserResource, RegisterUserResource
from .api.resources.reviews import ReviewResource, ReviewsResource
from .api.resources.review_plans import ReviewPlanResource
from .api.resources.review_teams import ReviewTeamResource
from .api.resources.review_progress import ReviewProgressResource
from .api.resources.citations import CitationResource, CitationsResource
from .api.resources.citation_screenings import CitationScreeningsResource, CitationsScreeningsResource
from .api.resources.citation_uploads import CitationUploadsResource
from .api.resources.fulltexts import FulltextResource, FulltextsResource
from .api.resources.fulltext_screenings import FulltextScreeningsResource, FulltextsScreeningsResource
from .api.resources.fulltext_uploads import FulltextUploadResource
from .api.resources.fulltexts_extracted_data import FulltextExtractedDataResource
from .api.resources.review_exports import ReviewExportResource


def create_app(config_name):
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    os.makedirs(config[config_name].FULLTEXT_UPLOAD_FOLDER, exist_ok=True)

    celery.conf.update(app.config)

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    api = Api(app, api_version='0.1.0', api_spec_url='/api/spec',
              title='colandr', description='REST API powering the colandr app')
    # api = swagger.docs(
    #     Api(app),
    #     apiVersion='0.1',
    #     api_spec_url='/spec',
    #     description='Colandr API')
    # api = Api(app)

    api.add_resource(RegisterUserResource, '/register')
    api.add_resource(ConfirmUserResource, '/confirm')
    api.add_resource(AuthTokenResource, '/authtoken')
    api.add_resource(UsersResource, '/users')
    api.add_resource(UserResource, '/users/<int:id>')
    api.add_resource(ReviewsResource, '/reviews')
    api.add_resource(ReviewResource, '/reviews/<int:id>')
    api.add_resource(ReviewTeamResource, '/reviews/<int:id>/team')
    api.add_resource(ReviewProgressResource, '/reviews/<int:id>/progress')
    api.add_resource(ReviewExportResource, '/reviews/<int:id>/export')
    api.add_resource(ReviewPlanResource, '/reviews/<int:id>/plan')
    api.add_resource(CitationsResource, '/citations')
    api.add_resource(CitationUploadsResource, '/citations/upload')
    api.add_resource(CitationResource, '/citations/<int:id>')
    api.add_resource(CitationsScreeningsResource, '/citations/screenings')
    api.add_resource(CitationScreeningsResource, '/citations/<int:id>/screenings')
    api.add_resource(FulltextsResource, '/fulltexts')
    api.add_resource(FulltextResource, '/fulltexts/<int:id>')
    api.add_resource(FulltextsScreeningsResource, '/fulltexts/screenings')
    api.add_resource(FulltextScreeningsResource, '/fulltexts/<int:id>/screenings')
    api.add_resource(FulltextUploadResource, '/fulltexts/<int:id>/upload')
    api.add_resource(FulltextExtractedDataResource, '/fulltexts/<int:id>/extracted_data')

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

    @app.errorhandler(422)
    def handle_validation_error(err):
        # The marshmallow.ValidationError is available on err.exc
        return jsonify({'errors': err.exc.messages}), 422

    return app
