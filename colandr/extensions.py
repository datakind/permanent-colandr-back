import celery
import flask
import flask_caching
import flask_jwt_extended
import flask_limiter
import flask_limiter.util
import flask_mail
import flask_migrate
import flask_sqlalchemy
import sqlalchemy.orm

from colandr.lib import flask_filesystem


class _BaseModel(sqlalchemy.orm.DeclarativeBase):
    # type_annotation_map = {dict[str, typing.Any]: sqlalchemy.dialects.postgresql.JSON}
    pass


cache = flask_caching.Cache()
db = flask_sqlalchemy.SQLAlchemy(model_class=_BaseModel)
limiter = flask_limiter.Limiter(
    flask_limiter.util.get_remote_address,
    default_limits=["1/second"],
    meta_limits=["1/minute", "10/hour"],
    strategy="fixed-window",
    storage_uri="memory://",  # TODO: use redis for storage?
)
jwt = flask_jwt_extended.JWTManager()
mail = flask_mail.Mail()
migrate = flask_migrate.Migrate()
filesystem = flask_filesystem.FileSystem()

review_model_cache = flask_caching.Cache(
    config={
        "CACHE_TYPE": "SimpleCache",
        "CACHE_DEFAULT_TIMEOUT": 0,
        "CACHE_THRESHOLD": 25,  # Maximum number of items
    },
)


def init_celery_app(app):
    class FlaskTask(celery.Task):
        retry_backoff = True
        retry_jitter = True

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = celery.Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config["CELERY"])
    celery_app.set_default()
    if not hasattr(app, "extensions"):
        app.extensions = {}
    app.extensions["celery"] = celery_app
    return celery_app


@limiter.request_filter
def header_whitelist() -> bool:
    return flask.request.endpoint in {"openapi.docs", "openapi.spec"}
