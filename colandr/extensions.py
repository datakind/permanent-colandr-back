# import typing

import celery
import flask_caching
import flask_jwt_extended
import flask_mail
import flask_migrate
import flask_sqlalchemy
import sqlalchemy.orm
# from sqlalchemy.dialects import postgresql
from flask import Flask


class _BaseModel(sqlalchemy.orm.DeclarativeBase):
    # type_annotation_map = {dict[str, typing.Any]: postgresql.JSON}
    pass


cache = flask_caching.Cache()
db = flask_sqlalchemy.SQLAlchemy(model_class=_BaseModel)
jwt = flask_jwt_extended.JWTManager()
mail = flask_mail.Mail()
migrate = flask_migrate.Migrate()

review_model_cache = flask_caching.Cache(config={
    'CACHE_TYPE': 'SimpleCache',
    'CACHE_DEFAULT_TIMEOUT': 3600 * 24,  # 24 hours
    'CACHE_THRESHOLD': 25  # Maximum number of items
})


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


def init_extensions(app: Flask) -> None:
    """Initialize all available Flask extensions."""
    cache.init_app(app)
    with app.app_context():
        cache.clear()
    db.init_app(app)
    jwt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    # Initialize the model cache
    review_model_cache.init_app(app)
