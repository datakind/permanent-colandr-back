from colandr.extensions import db, mail, migrate
from colandr.api import api_

# import logging
# import os

# from celery import Celery
# from flask import g, Flask, jsonify, send_from_directory
# from flask_restx import Api
# from flask_mail import Mail
# from flask_migrate import Migrate
# from flask_sqlalchemy import SQLAlchemy
# from marshmallow import fields as ma_fields
# from marshmallow.validate import Range
# from webargs.flaskparser import use_kwargs
# from sqlalchemy.exc import SQLAlchemyError

# api_ = Api(
#     version='1.0', prefix='/api', doc='/docs',
#     default_mediatype='application/json',
#     title='colandr', description='REST API powering the colandr app',
#     )
# db = SQLAlchemy()
# mail = Mail()
# migrate = Migrate()

# from .config import configs, Config

# celery = Celery(__name__, broker=Config.CELERY_BROKER_URL)

# from .lib import constants
# from .lib.utils import get_rotating_file_handler, get_console_handler

# from .api.errors import not_found_error, forbidden_error
# from .api.resources.user_registration import ns as register_ns
# from .api.resources.password_reset import ns as reset_ns
# from .api.authentication import ns as authtoken_ns
# from .api.resources.users import ns as users_ns
# from .api.resources.reviews import ns as reviews_ns
# from .api.resources.review_teams import ns as review_teams_ns
# from .api.resources.review_progress import ns as review_progress_ns
# from .api.resources.review_exports import ns as review_exports_ns
# from .api.resources.review_plans import ns as review_plans_ns
# from .api.resources.studies import ns as studies_ns
# from .api.resources.study_tags import ns as study_tags_ns
# from .api.resources.citations import ns as citations_ns
# from .api.resources.citation_imports import ns as citation_imports_ns
# from .api.resources.citation_screenings import ns as citation_screenings_ns
# from .api.resources.fulltexts import ns as fulltexts_ns
# from .api.resources.fulltext_uploads import ns as fulltext_uploads_ns
# from .api.resources.fulltext_screenings import ns as fulltext_screenings_ns
# from .api.resources.data_extractions import ns as data_extractions_ns


# def create_app(config_name="dev"):
#     app = Flask('colandr')
#     config = configs[config_name]()
#     app.config.from_object(config)
#     config.init_app(app)
#     os.makedirs(config.FULLTEXT_UPLOADS_DIR, exist_ok=True)
#     os.makedirs(config.RANKING_MODELS_DIR, exist_ok=True)

#     # app.logger.addHandler(
#     #     get_rotating_file_handler(os.path.join(config.LOGS_DIR, config.LOG_FILENAME)))
#     # app.logger.addHandler(get_console_handler())
#     # app.logger.addFilter(logging.Filter('colandr'))
#     # # app.logger.propagate = False

#     celery.conf.update(app.config)

#     db.init_app(app)
#     mail.init_app(app)
#     migrate.init_app(app, db)
#     api_.init_app(app)

#     # api_.add_namespace(register_ns)
#     # api_.add_namespace(reset_ns)
#     # api_.add_namespace(authtoken_ns)
#     # api_.add_namespace(users_ns)
#     # api_.add_namespace(reviews_ns)
#     # api_.add_namespace(review_teams_ns)
#     # api_.add_namespace(review_progress_ns)
#     # api_.add_namespace(review_exports_ns)
#     # api_.add_namespace(review_plans_ns)
#     # api_.add_namespace(studies_ns)
#     # api_.add_namespace(study_tags_ns)
#     # api_.add_namespace(citations_ns)
#     # api_.add_namespace(citation_imports_ns)
#     # api_.add_namespace(citation_screenings_ns)
#     # api_.add_namespace(fulltexts_ns)
#     # api_.add_namespace(fulltext_uploads_ns)
#     # api_.add_namespace(fulltext_screenings_ns)
#     # api_.add_namespace(data_extractions_ns)

#     @app.route('/')
#     def home():
#         return "Welcome to Colandr's API!"

#     # @app.route('/fulltexts/<int:id>/upload', methods=['GET'])
#     # @fulltext_uploads_ns.doc(
#     #     params={
#     #         'review_id': {'in': 'query', 'type': 'integer', 'required': False,
#     #                       'description': 'unique identifier for review whose fulltext upload is to be fetched'},
#     #         },
#     #     produces=['application/json'],
#     #     responses={
#     #         200: 'successfully got uploaded fulltext content file',
#     #         404: 'no fulltext content file with matching id was found',
#     #         }
#     #     )
#     # @use_kwargs({
#     #     'id': ma_fields.Int(
#     #         required=True, location='view_args',
#     #         validate=Range(min=1, max=constants.MAX_INT)),
#     #     'review_id': ma_fields.Int(
#     #         missing=None,
#     #         validate=Range(min=1, max=constants.MAX_INT)),
#     #     })
#     # def get_uploaded_fulltext_file(id, review_id):
#     #     """get fulltext content file for a single fulltext by id"""
#     #     filename = None
#     #     if review_id is None:
#     #         for dirname, _, filenames in os.walk(app.config['FULLTEXT_UPLOADS_DIR']):
#     #             for ext in app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
#     #                 fname = '{}{}'.format(id, ext)
#     #                 if fname in filenames:
#     #                     filename = fname
#     #                     upload_dir = dirname
#     #                     break
#     #     else:
#     #         # authenticate current user
#     #         from colandr.models import Review
#     #         review = db.session.query(Review).get(review_id)
#     #         if not review:
#     #             return not_found_error('<Review(id={})> not found'.format(review_id))
#     #         if (g.current_user.is_admin is False and
#     #                 review.users.filter_by(id=g.current_user.id).one_or_none() is None):
#     #             return forbidden_error(
#     #                 '{} forbidden to get this review\'s fulltexts'.format(g.current_user))
#     #         upload_dir = os.path.join(
#     #             app.config['FULLTEXT_UPLOADS_DIR'], str(review_id))
#     #         for ext in app.config['ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS']:
#     #             fname = '{}{}'.format(id, ext)
#     #             if os.path.isfile(os.path.join(upload_dir, fname)):
#     #                 filename = fname
#     #                 break
#     #     if not filename:
#     #         return not_found_error(
#     #             'no uploaded file for <Fulltext(id={})> found'.format(id))
#     #     return send_from_directory(upload_dir, filename)

#     # @app.errorhandler(Exception)
#     # def handle_error(err):
#     #     app.logger.error(str(err))
#     #     return jsonify({'errors': str(err)}), 500

#     # @app.errorhandler(SQLAlchemyError)
#     # def handle_sqlalchemy_error(err):
#     #     app.logger.error('db unable to handle request! rolling back...')
#     #     db.session.rollback()
#     #     db.session.remove()
#     #     return jsonify({'errors': str(err)}), 500

#     # @app.errorhandler(422)
#     # def handle_validation_error(err):
#     #     return jsonify({'errors': err.exc.messages}), 422

#     # @app.teardown_request
#     # def teardown_request(err):
#     #     if err:
#     #         logger.error('got server error while handling request! rolling back...\n%s', err.message)
#     #         db.session.rollback()
#     #         db.session.remove()
#     #         return jsonify({'errors': err.message}), 500
#     #     db.session.remove()

#     return app
