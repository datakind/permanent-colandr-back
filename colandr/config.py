# SQLALCHEMY_DATABASE_URI config option: must be an environment variable
# format: 'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# COLANDR_SECRET_KEY config option: must be an environment variable
# treat it like a password, can be whatever, just make it hard to guess

import os


class Config(object):
    SECRET_KEY = os.environ.get('COLANDR_SECRET_KEY') or 'burton-bob-caitlin-ray-sam'
    BCRYPT_LOG_ROUNDS = 12
    SSL_DISABLE = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ECHO = True
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    LOGGER_NAME = 'colandr-api'
    JSON_AS_ASCII = False
    FULLTEXT_UPLOAD_FOLDER = '~/colandr/uploads'
    ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS = {'txt', 'pdf'}
    # MAIL_SERVER = 'smtp.googlemail.com'
    # MAIL_PORT = 587
    # MAIL_USE_TLS = True
    # MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    # MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    # FLASKY_MAIL_SUBJECT_PREFIX = '[Flasky]'
    # FLASKY_MAIL_SENDER = 'Flasky Admin <flasky@example.com>'
    # FLASKY_ADMIN = os.environ.get('FLASKY_ADMIN')
    # FLASKY_POSTS_PER_PAGE = 20
    # FLASKY_FOLLOWERS_PER_PAGE = 50
    # FLASKY_COMMENTS_PER_PAGE = 30
    # FLASKY_SLOW_DB_QUERY_TIME = 0.5

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    # TODO: use different databases for different configs?
    SQLALCHEMY_DATABASE_URI = os.environ['SQLALCHEMY_DATABASE_URI']


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    # TODO: use different databases for difference configs?
    SQLALCHEMY_DATABASE_URI = os.environ['SQLALCHEMY_DATABASE_URI']


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # TODO: use different databases for difference configs?
    SQLALCHEMY_DATABASE_URI = os.environ['SQLALCHEMY_DATABASE_URI']


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    }
