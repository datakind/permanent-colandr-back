# config options taken from environment variables:
# - COLANDR_DATABASE_URI
#     - format: 'postgresql://{DB_USER}:{DB_PASS}@{DB_HOST}:{DB_PORT}/{DB_NAME}'
# - COLANDR_SECRET_KEY
#     - treat it like a password, can be whatever, just make it hard to guess
# - COLANDR_PASSWORD_SALT
#     - also like a password, can be whatever, just make it hard to guess
# - COLANDR_MAIL_USERNAME
# - COLANDR_MAIL_PASSWORD

import os


class Config(object):
    SECRET_KEY = os.environ.get('COLANDR_SECRET_KEY')
    PASSWORD_SALT = os.environ.get('COLANDR_PASSWORD_SALT')
    BCRYPT_LOG_ROUNDS = 12
    SSL_DISABLE = False
    LOGGER_NAME = 'colandr-api'
    JSON_AS_ASCII = False
    CONFIRM_TOKEN_EXPIRATION = 3600

    # celery+redis config
    CELERY_BROKER_URL = 'redis://localhost:6379/0'
    CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
    CELERY_ACCEPT_CONTENT = ['json']
    CELERY_TASK_SERIALIZER = 'json'
    CELERY_RESULT_SERIALIZER = 'json'
    CELERYD_LOG_COLOR = False

    # sql db config
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # files-on-disk config
    FULLTEXT_UPLOAD_FOLDER = os.path.join(
        os.environ.get('HOME') or os.path.expanduser('~/'),
        'colandr/fulltexts/uploads')
    ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS = {'.txt', '.pdf'}
    MAX_CONTENT_LENGTH = 40 * 1024 * 1024  # 40MB file upload limit
    DEDUPE_MODELS_FOLDER = os.path.join(
        os.environ.get('HOME') or os.path.expanduser('~/'),
        'colandr/dedupe')

    # email server config
    MAIL_SERVER = 'smtp.googlemail.com'
    MAIL_PORT = 587
    MAIL_USE_TLS = True
    MAIL_USE_SSL = False
    MAIL_USERNAME = os.environ.get('COLANDR_MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('COLANDR_MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = 'Colandr <{}>'.format(MAIL_USERNAME)
    MAIL_SUBJECT_PREFIX = '[Colandr]'
    MAIL_ADMINS = ['burtdewilde@gmail.com']

    @staticmethod
    def init_app(app):
        pass


class DevelopmentConfig(Config):
    DEBUG = True
    TESTING = False
    # TODO: use different databases for different configs?
    SQLALCHEMY_DATABASE_URI = os.environ['COLANDR_DATABASE_URI']


class TestingConfig(Config):
    DEBUG = False
    TESTING = True
    # TODO: use different databases for difference configs?
    SQLALCHEMY_DATABASE_URI = os.environ['COLANDR_DATABASE_URI']
    SQLALCHEMY_ECHO = True


class ProductionConfig(Config):
    DEBUG = False
    TESTING = False
    # TODO: use different databases for difference configs?
    SQLALCHEMY_DATABASE_URI = os.environ['COLANDR_DATABASE_URI']


config = {
    'development': DevelopmentConfig,
    'testing': TestingConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig,
    }
