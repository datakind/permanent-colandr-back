import datetime
import os

from dotenv import load_dotenv


# load `.env` file based on `.env.example` containing config values
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


# flask config
TESTING = False
SECRET_KEY = os.environ["COLANDR_SECRET_KEY"]
MAX_CONTENT_LENGTH = 50 * 1024 * 1024  # 50MB file upload limit
LOG_LEVEL = os.environ.get("COLANDR_LOG_LEVEL", "info").upper()
# PROPAGATE_EXCEPTIONS = True  # may be needed for error handlers to work

# sql database config
SQLALCHEMY_DATABASE_URI = os.environ["COLANDR_DATABASE_URI"]
SQLALCHEMY_ENGINE_OPTIONS = {}
SQLALCHEMY_ECHO = False

# celery+redis config
CELERY = {
    "broker_url": os.environ.get(
        "COLANDR_CELERY_BROKER_URL", "redis://localhost:6379/0"
    ),
    "result_backend": os.environ.get(
        "COLANDR_CELERY_RESULT_BACKEND", "redis://localhost:6379/0"
    ),
    "accept_content": ["json"],
    "task_serializer": "json",
    "result_serializer": "json",
    # ref: https://steve.dignam.xyz/2023/05/20/many-problems-with-celery
    "worker_prefetch_multiplier": 1,
    "task_acks_late": True,
    "task_create_missing_queues": True,
}

# cache config
CACHE_TYPE = "SimpleCache"
# TODO: figure out if/how we want to use redis for caching
# CACHE_TYPE = "RedisCache",
# CACHE_REDIS_HOST = os.environ.get("COLANDR_REDIS_HOST", "localhost")

# api auth keys config
FE_APP_SITE = os.environ.get("COLANDR_FE_APP_SITE")
JWT_SECRET_KEY = os.environ.get("COLANDR_JWT_SECRET_KEY")
JWT_ACCESS_TOKEN_EXPIRES = datetime.timedelta(hours=4)
JWT_REFRESH_TOKEN_EXPIRES = datetime.timedelta(days=3)
JWT_TOKEN_LOCATION = "headers"
# configure auth header structure: "{JWT_HEADER_NAME}: {JWT_HEADER_TYPE} {JWT_TOKEN}"
JWT_HEADER_NAME = "Authorization"
JWT_HEADER_TYPE = "Bearer"

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

# file storage config
FILESYSTEM_PROTOCOL = os.environ.get("COLANDR_FILESYSTEM_PROTOCOL", "file")
FILESYSTEM_STORAGE_OPTIONS = {
    "file": {"auto_mkdir": False},
    "gcs": {
        "project": os.environ.get("COLANDR_FILESYSTEM_GCS_PROJECT"),
        "token": os.environ.get("COLANDR_FILESYSTEM_GCS_TOKEN"),
        "endpoint_url": os.environ.get("COLANDR_FILESYSTEM_GCS_ENDPOINT_URL"),
        "access": "read_write",
        "cache_timeout": 3600,
    },
}
FILESYSTEM_ROOT_DIR = os.environ.get("COLANDR_FILESYSTEM_ROOT_DIR", "/tmp")
FULLTEXT_UPLOADS_DIR = os.path.join(FILESYSTEM_ROOT_DIR, "colandr_data", "fulltexts")
ALLOWED_CITATION_UPLOAD_EXTENSIONS = {".ris", ".txt", ".bib", ".csv", ".tsv"}
ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS = {".txt", ".pdf"}
# TODO: figure out root dir vs app dir
COLANDR_APP_DIR = os.environ.get("COLANDR_APP_DIR", "/tmp")
DEDUPE_MODELS_DIR = os.path.join(
    COLANDR_APP_DIR, "colandr_data", "dedupe-v2", "model_202407"
)
RANKER_MODELS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "ranker_models")

# metadata extraction config
METADATA_THRESHOLD = float(os.environ.get("COLANDR_METADATA_THRESHOLD", "0.65"))
METADATA_INCREASE_TO_RETRAIN = int(
    os.environ.get("COLANDR_METADATA_INCREASE_TO_RETRAIN", "5")
)
METADATA_MIN_TO_TRAIN = int(os.environ.get("COLANDR_METADATA_MIN_TO_TRAIN", "40"))
