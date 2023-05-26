import logging
import os

from flask import Flask

from colandr import cli, errors, extensions
from colandr.config import configs, Config
from colandr.lib.utils import get_rotating_file_handler, get_console_handler


def create_app(config_name="dev"):
    app = Flask('colandr')
    config = configs[config_name]()
    app.config.from_object(config)
    config.init_app(app)

    configure_logging(app)
    register_extensions(app)
    app.register_blueprint(cli.bp)
    app.register_blueprint(errors.bp)

    @app.route('/')
    def home():
        return "Welcome to Colandr's API!"

    return app


def configure_logging(app):
    """Configure logging on ``app`` ."""
    # app.logger.addHandler(
    #     get_rotating_file_handler(
    #         os.path.join(app.config.LOGS_DIR, app.config.LOG_FILENAME)
    #     )
    # )
    app.logger.addHandler(get_console_handler())
    app.logger.addFilter(logging.Filter("colandr"))
    # app.logger.propagate = False


def register_extensions(app):
    """Register flask extensions on ``app`` ."""
    extensions.db.init_app(app)
    extensions.mail.init_app(app)
    extensions.migrate.init_app(app, extensions.db)
    extensions.api_.init_app(app)
