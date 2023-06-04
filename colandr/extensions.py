import os

import celery
import flask_caching
import flask_mail
import flask_migrate
import flask_praetorian
import flask_sqlalchemy


cache = flask_caching.Cache(
    config={
        "CACHE_TYPE": "RedisCache",
        "CACHE_REDIS_HOST": os.environ.get("COLANDR_REDIS_HOST", "localhost"),
    },
)
db = flask_sqlalchemy.SQLAlchemy()
guard = flask_praetorian.Praetorian()
mail = flask_mail.Mail()
migrate = flask_migrate.Migrate()


def init_celery_app(app):
    class FlaskTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery_app = celery.Celery(app.name, task_cls=FlaskTask)
    celery_app.config_from_object(app.config, namespace="CELERY")
    celery_app.set_default()
    if not hasattr(app, "extensions"):
        app.extensions = {}
    app.extensions["celery"] = celery_app
    return celery_app
