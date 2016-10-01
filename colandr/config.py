# SQLALCHEMY_DATABASE_URI config option: must be an environment variable
# format: 'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# COLANDR_SECRET_KEY config option: must be an environment variable
# treat it like a password, can be whatever, just make it hard to guess

import os


class Config(object):
    SECRET_KEY = os.environ.get('COLANDR_SECRET_KEY') or 'burton-bob-caitlin-ray-sam'
    BCRYPT_LOG_ROUNDS = 12
    SSL_DISABLE = False
    LOGGER_NAME = 'colandr-api'
    JSON_AS_ASCII = False
    # sql db config
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True
    # file upload config
    FULLTEXT_UPLOAD_FOLDER = os.path.join(
        os.environ.get('HOME') or os.path.expanduser('~/'),
        'colandr/fulltexts/uploads')
    ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS = {'.txt', '.pdf'}
    MAX_CONTENT_LENGTH = 40 * 1024 * 1024  # 40MB file upload limit
    # email server config
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('COLANDR_MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('COLANDR_MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'Colandr <burtdewilde@gmail.com>'
    MAIL_ADMINS = ['burtdewilde@gmail.com']
    MAIL_SUBJECT_PREFIX = '[Colandr]'

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
    SQLALCHEMY_ECHO = True


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
