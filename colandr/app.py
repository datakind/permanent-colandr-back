import logging
import sys
import typing as t

import apiflask as af
import flask
import flask.logging

from colandr import cli, config, errors, extensions
from colandr.api import v1
from colandr.apis import api_v1


def create_app(config_overrides: t.Optional[dict[str, t.Any]] = None) -> flask.Flask:
    # app = _create_app_v1(config_overrides)
    app = _create_app_v1_1(config_overrides)
    return app


def _create_app_v1(
    config_overrides: t.Optional[dict[str, t.Any]] = None,
) -> flask.Flask:
    app = flask.Flask("colandr")
    app.config.from_object(config)
    if config_overrides:
        app.config.update(config_overrides)

    _configure_logging(app)
    _register_extensions(app)
    api_v1.init_app(app)
    app.register_blueprint(cli.bp)
    app.register_blueprint(errors.bp)

    return app


def _create_app_v1_1(
    config_overrides: t.Optional[dict[str, t.Any]] = None,
) -> flask.Flask:
    app = af.APIFlask(
        "colandr",
        title="Colandr API",
        version="1.1",
        docs_ui="swagger-ui",
        docs_path="/docs",
    )
    app.config.from_object(config)
    if config_overrides:
        app.config.update(config_overrides)

    _configure_logging(app)
    _register_extensions(app)
    v1.register_api_blueprints(app)
    app.register_blueprint(cli.bp)
    app.register_blueprint(errors.bp)
    app.security_schemes = {
        "TokenAuth": {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    }
    # TODO: authenticate for openapi interface when not in dev
    # if app.config["BUILD_TARGET"] != "dev":
    #     app.config["SPEC_DECORATORS"] = [app.auth_required(auth)]

    return app


def _configure_logging(app: flask.Flask) -> None:
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

    # filter logging for a particular endpoint
    class EndpointFilter(logging.Filter):
        def __init__(self, path: str, *args: t.Any, **kwargs: t.Any):
            super().__init__(*args, **kwargs)
            self._path = path

        def filter(self, record: logging.LogRecord) -> bool:
            return record.getMessage().find(self._path) == -1

    werkzeug_logger = logging.getLogger("werkzeug")
    werkzeug_logger.addFilter(EndpointFilter("/health"))
    loggers = logging.root.manager.loggerDict
    if "gunicorn.access" in loggers:
        gunicorn_logger = logging.getLogger("gunicorn.access")
        gunicorn_logger.addFilter(EndpointFilter("/health"))


def _register_extensions(app: flask.Flask) -> None:
    """Register flask extensions on ``app`` ."""
    extensions.cache.init_app(app)
    with app.app_context():
        extensions.cache.clear()
    extensions.db.init_app(app)
    extensions.limiter.init_app(app)
    extensions.jwt.init_app(app)
    extensions.mail.init_app(app)
    extensions.migrate.init_app(app, extensions.db)
    extensions.review_model_cache.init_app(app)
    extensions.filesystem.init_app(app)
    extensions.init_celery_app(app)
