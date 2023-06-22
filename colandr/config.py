import os

from dotenv import load_dotenv


# load `.env` file based on `.env.example` containing config values
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


class Config:
    TESTING = False
    SECRET_KEY = os.environ["COLANDR_SECRET_KEY"]
    PASSWORD_SALT = os.environ.get("COLANDR_PASSWORD_SALT")
    BCRYPT_LOG_ROUNDS = 12
    SSL_DISABLE = False
    LOGGER_NAME = "colandr"
    JSON_AS_ASCII = False
    CONFIRM_TOKEN_EXPIRATION = 3600
    APP_URL_DOMAIN = "http://localhost:5001/api"

    # celery+redis config
    CELERY_BROKER_URL = os.environ.get(
        "COLANDR_CELERY_BROKER_URL", "redis://localhost:6379/0"
    )
    CELERY_RESULT_BACKEND = os.environ.get(
        "COLANDR_CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    )
    CELERY_ACCEPT_CONTENT = ["json"]
    CELERY_TASK_SERIALIZER = "json"
    CELERY_RESULT_SERIALIZER = "json"
    CELERYD_LOG_COLOR = False

    # sql db config
    SQLALCHEMY_DATABASE_URI = os.environ["COLANDR_DATABASE_URI"]
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    SQLALCHEMY_ECHO = False
    SQLALCHEMY_RECORD_QUERIES = True
    SQLALCHEMY_TRACK_MODIFICATIONS = True

    # authentication config
    JWT_ACCESS_LIFESPAN = {"hours": 3}
    JWT_REFRESH_LIFESPAN = {"days": 7}

    # files-on-disk config
    COLANDR_APP_DIR = os.environ.get("COLANDR_APP_DIR", "/tmp")
    LOGS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "logs")
    LOG_FILENAME = "colandr.log"
    DEDUPE_MODELS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "dedupe")
    RANKING_MODELS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "ranking_models")
    CITATIONS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "citations")
    FULLTEXT_UPLOADS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "fulltexts")
    ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS = {".txt", ".pdf"}
    MAX_CONTENT_LENGTH = 40 * 1024 * 1024  # 40MB file upload limit

    # email server config
    MAIL_SERVER = os.environ.get("COLANDR_MAIL_SERVER")
    MAIL_PORT = os.environ.get("COLANDR_MAIL_PORT")
    MAIL_USE_TLS = (
        bool(int(os.environ["COLANDR_MAIL_USE_TLS"]))
        if os.environ.get("COLANDR_MAIL_USE_TLS")
        else None
    )
    MAIL_USE_SSL = (
        bool(int(os.environ["COLANDR_MAIL_USE_SSL"]))
        if os.environ.get("COLANDR_MAIL_USE_SSL")
        else None
    )
    MAIL_USERNAME = os.environ.get("COLANDR_MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("COLANDR_MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = f"colandr <{MAIL_USERNAME}>"
    MAIL_SUBJECT_PREFIX = "[colandr]"
    MAIL_ADMINS = ["burtdewilde@gmail.com"]

    @staticmethod
    def init_app(app):
        pass


class ProductionConfig(Config):
    FLASK_ENV = "production"


class DevelopmentConfig(Config):
    FLASK_ENV = "development"
    LOGGER_NAME = "dev-colandr"
    LOG_FILENAME = "dev-colandr.log"


class TestingConfig(Config):
    TESTING = True
    LOGGER_NAME = "test-colandr"
    LOG_FILENAME = "test-colandr.log"
    SQLALCHEMY_ECHO = True


configs = {
    "dev": DevelopmentConfig,
    "test": TestingConfig,
    "prod": ProductionConfig,
    "default": ProductionConfig,
}
