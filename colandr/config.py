import os

from dotenv import load_dotenv


# load `.env` file based on `.env.example` containing config values
basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
load_dotenv(os.path.join(basedir, ".env"))


# flask config
TESTING = False
SECRET_KEY = os.environ["COLANDR_SECRET_KEY"]
MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25MB file upload limit
LOG_LEVEL = os.environ.get("COLANDR_LOG_LEVEL", "info").upper()

# sql database config
SQLALCHEMY_DATABASE_URI = os.environ["COLANDR_DATABASE_URI"]
# TODO: figure out how to properly set this setting in a way that works
# from inside and outside docker
# DB_USER = os.environ["COLANDR_DB_USER"]
# DB_PASSWORD = os.environ["COLANDR_DB_PASSWORD"]
# DB_HOST = os.environ["COLANDR_DB_HOST"]
# DB_NAME = os.environ["COLANDR_DB_NAME"]
# SQLALCHEMY_DATABASE_URI = (
#     f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:5432/{DB_NAME}"
# )
SQLALCHEMY_ECHO = False
# TODO: figure out why future-style sqlalchemy usage fails catastrophically
# SQLALCHEMY_ENGINE_OPTIONS = {"future": True}

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
}

# cache config
CACHE_TYPE = "SimpleCache"
# TODO: figure out if/how we want to use redis for caching
# CACHE_TYPE = "RedisCache",
# CACHE_REDIS_HOST = os.environ.get("COLANDR_REDIS_HOST", "localhost")

# api auth keys config
JWT_ACCESS_LIFESPAN = {"hours": 3}
JWT_REFRESH_LIFESPAN = {"days": 7}

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

# files-on-disk config
COLANDR_APP_DIR = os.environ.get("COLANDR_APP_DIR", "/tmp")
DEDUPE_MODELS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "dedupe")
RANKING_MODELS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "ranking_models")
CITATIONS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "citations")
FULLTEXT_UPLOADS_DIR = os.path.join(COLANDR_APP_DIR, "colandr_data", "fulltexts")
ALLOWED_FULLTEXT_UPLOAD_EXTENSIONS = {".txt", ".pdf"}
