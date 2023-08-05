import logging
import sys
from typing import Any, Optional

import flask
import flask.logging

from colandr import cli, config, errors, extensions, models
from colandr.api import api_


def create_app(config_overrides: Optional[dict[str, Any]] = None) -> flask.Flask:
    app = flask.Flask("colandr")
    app.config.from_object(config)
    if config_overrides:
        app.config.update(config_overrides)

    configure_logging(app)
    register_extensions(app)
    app.register_blueprint(cli.bp)
    app.register_blueprint(errors.bp)

    return app


def configure_logging(app: flask.Flask) -> None:
    """Configure logging on ``app`` ."""
    if app.logger.handlers:
        app.logger.removeHandler(flask.logging.default_handler)

    handler = logging.StreamHandler(stream=sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(levelname)s - %(module)s.%(funcName)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    handler.setLevel(app.config["LOG_LEVEL"])
    app.logger.addHandler(handler)
    # TODO: do we *want* to filter to just colandr's logging, or others' (deps') too?
    app.logger.addFilter(logging.Filter("colandr"))


def register_extensions(app: flask.Flask) -> None:
    """Register flask extensions on ``app`` ."""
    extensions.cache.init_app(app)
    with app.app_context():
        extensions.cache.clear()
    extensions.db.init_app(app)
    extensions.guard.init_app(app, user_class=models.User)
    extensions.mail.init_app(app)
    extensions.migrate.init_app(app, extensions.db)
    api_.init_app(app)
    extensions.init_celery_app(app)
