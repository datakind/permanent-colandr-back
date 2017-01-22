import os

from celery import Celery
from flask import Flask, jsonify, send_from_directory
from flask_restplus import Api
from flask_mail import Mail
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy

api_ = Api(version='1.0', prefix='/api', doc='/',
           default_mediatype='application/json',
           title='colandr', description='REST API powering the colandr app',
           )
db = SQLAlchemy()
mail = Mail()
migrate = Migrate()

from .config import config, Config

celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

from .lib.utils import get_rotating_file_logger
# from .api.authentication import AuthTokenResource
# from .api.errors import no_data_found
# from .api.resources.user_registration import UserRegistrationResource, ConfirmUserRegistrationResource
# from .api.resources.password_reset import PasswordResetResource, ConfirmPasswordResetResource
# from .api.resources.users import UserResource, UsersResource
# from .api.resources.reviews import ReviewResource, ReviewsResource
# from .api.resources.review_plans import ReviewPlanResource
# from .api.resources.review_teams import ReviewTeamResource, ConfirmReviewTeamInviteResource
# from .api.resources.review_progress import ReviewProgressResource
# from .api.resources.studies import StudyResource, StudiesResource
# from .api.resources.study_tags import StudyTagsResource
# from .api.resources.citations import CitationResource, CitationsResource
# from .api.resources.citation_screenings import CitationScreeningsResource, CitationsScreeningsResource
# from .api.resources.citation_imports import CitationsImportsResource
# from .api.resources.fulltexts import FulltextResource
# from .api.resources.fulltext_screenings import FulltextScreeningsResource, FulltextsScreeningsResource
# from .api.resources.fulltext_uploads import FulltextUploadResource
# from .api.resources.data_extractions import DataExtractionResource
# from .api.resources.review_exports import ReviewExportPrismaResource, ReviewExportStudiesResource

logger = get_rotating_file_logger(
    'colandr', os.path.join(Config.LOGS_FOLDER, 'colandr.log'), level='info')

from colandr.api.resources.user_registration import ns as register_ns
from colandr.api.resources.password_reset import ns as reset_ns
from colandr.api.authentication import ns as authtoken_ns
from colandr.api.resources.users import ns as users_ns
from colandr.api.resources.reviews import ns as reviews_ns
from colandr.api.resources.review_teams import ns as review_teams_ns
from colandr.api.resources.review_progress import ns as review_progress_ns
from colandr.api.resources.review_exports import ns as review_exports_ns
from colandr.api.resources.review_plans import ns as review_plans_ns


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

    # api_.add_resource(UserRegistrationResource, '/register')
    # api_.add_resource(ConfirmUserRegistrationResource, '/register/<token>')
    # api_.add_resource(PasswordResetResource, '/reset')
    # api_.add_resource(ConfirmPasswordResetResource, '/reset/<token>')
    # api_.add_resource(AuthTokenResource, '/authtoken')
    # api_.add_resource(UsersResource, '/users')
    # api_.add_resource(UserResource, '/users/<int:id>')
    # api_.add_resource(ReviewsResource, '/reviews')
    # api_.add_resource(ReviewResource, '/reviews/<int:id>')
    # api_.add_resource(ReviewTeamResource, '/reviews/<int:id>/team')
    # api_.add_resource(ConfirmReviewTeamInviteResource, '/reviews/<int:id>/team/confirm')
    # api_.add_resource(ReviewProgressResource, '/reviews/<int:id>/progress')
    # api_.add_resource(ReviewExportPrismaResource, '/reviews/<int:id>/export_prisma')
    # api_.add_resource(ReviewExportStudiesResource, '/reviews/<int:id>/export_studies')
    # api_.add_resource(ReviewPlanResource, '/reviews/<int:id>/plan')
    # api_.add_resource(StudiesResource, '/studies')
    # api_.add_resource(StudyTagsResource, '/studies/tags')
    # api_.add_resource(StudyResource, '/studies/<int:id>')
    # api_.add_resource(CitationsResource, '/citations')
    # api_.add_resource(CitationsImportsResource, '/citations/imports')
    # api_.add_resource(CitationResource, '/citations/<int:id>')
    # api_.add_resource(CitationsScreeningsResource, '/citations/screenings')
    # api_.add_resource(CitationScreeningsResource, '/citations/<int:id>/screenings')
    # api_.add_resource(FulltextResource, '/fulltexts/<int:id>')
    # api_.add_resource(FulltextsScreeningsResource, '/fulltexts/screenings')
    # api_.add_resource(FulltextScreeningsResource, '/fulltexts/<int:id>/screenings')
    # api_.add_resource(FulltextUploadResource, '/fulltexts/<int:id>/upload')
    # api_.add_resource(DataExtractionResource, '/data_extracton/<int:id>')
    #
    # @app.route('/fulltexts/<int:id>/upload', methods=['GET'])
    # @api_.doc(tags=['fulltexts'], params={'id': 'study id'})
    # def get_uploaded_fulltext_file(id):
    #     filename = None
    #     upload_dir = app.config['FULLTEXT_UPLOAD_FOLDER']
    #     for ext in app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
    #         fname = '{}{}'.format(id, ext)
    #         if os.path.isfile(os.path.join(upload_dir, fname)):
    #             filename = fname
    #             break
    #     if not filename:
    #         return no_data_found(
    #             'no uploaded file for <Fulltext(id={})> found'.format(id))
    #     return send_from_directory(upload_dir, filename)

    @app.errorhandler(422)
    def handle_validation_error(err):
        # The marshmallow.ValidationError is available on err.exc
        return jsonify({'errors': err.exc.messages}), 422

    return app
