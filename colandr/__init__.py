import os

from celery import Celery
from flask import Flask, jsonify, send_from_directory
from flask_restplus import Api
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

api_ = Api(
    version='1.0', prefix='/api', doc='/docs',
    default_mediatype='application/json',
    title='colandr', description='REST API powering the colandr app',
    )
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()

from .config import config, Config

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

from .lib.utils import get_rotating_file_logger
from .api.errors import no_data_found

from colandr.api.resources.user_registration import ns as register_ns
from colandr.api.resources.password_reset import ns as reset_ns
from colandr.api.authentication import ns as authtoken_ns
from colandr.api.resources.users import ns as users_ns
from colandr.api.resources.reviews import ns as reviews_ns
from colandr.api.resources.review_teams import ns as review_teams_ns
from colandr.api.resources.review_progress import ns as review_progress_ns
from colandr.api.resources.review_exports import ns as review_exports_ns
from colandr.api.resources.review_plans import ns as review_plans_ns
from colandr.api.resources.studies import ns as studies_ns
from colandr.api.resources.study_tags import ns as study_tags_ns
from colandr.api.resources.citations import ns as citations_ns
from colandr.api.resources.citation_imports import ns as citation_imports_ns
from colandr.api.resources.citation_screenings import ns as citation_screenings_ns
from colandr.api.resources.fulltexts import ns as fulltexts_ns
from colandr.api.resources.fulltext_uploads import ns as fulltext_uploads_ns
from colandr.api.resources.fulltext_screenings import ns as fulltext_screenings_ns
from colandr.api.resources.data_extractions import ns as data_extractions_ns


logger = get_rotating_file_logger(
    'colandr', os.path.join(Config.LOGS_FOLDER, 'colandr.log'), level='info')


def create_app(config_name):
    app = Flask('colandr')
    app.config.from_object(config[config_name])
    config[config_name].init_app(app)
    os.makedirs(config[config_name].FULLTEXT_UPLOAD_FOLDER, exist_ok=True)

    celery.conf.update(app.config)

    db.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)
    api_.init_app(app)

    api_.add_namespace(register_ns)
    api_.add_namespace(reset_ns)
    api_.add_namespace(authtoken_ns)
    api_.add_namespace(users_ns)
    api_.add_namespace(reviews_ns)
    api_.add_namespace(review_teams_ns)
    api_.add_namespace(review_progress_ns)
    api_.add_namespace(review_exports_ns)
    api_.add_namespace(review_plans_ns)
    api_.add_namespace(studies_ns)
    api_.add_namespace(study_tags_ns)
    api_.add_namespace(citations_ns)
    api_.add_namespace(citation_imports_ns)
    api_.add_namespace(citation_screenings_ns)
    api_.add_namespace(fulltexts_ns)
    api_.add_namespace(fulltext_uploads_ns)
    api_.add_namespace(fulltext_screenings_ns)
    api_.add_namespace(data_extractions_ns)

    @app.route('/fulltexts/<int:id>/upload', methods=['GET'])
    @fulltext_uploads_ns.doc(
        produces=['application/json'],
        responses={
            200: 'successfully got uploaded fulltext content file',
            404: 'no fulltext content file with matching id was found',
            }
        )
    def get_uploaded_fulltext_file(id):
        """get fulltext content file for a single fulltext by id"""
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
