from flask import Blueprint, current_app, jsonify
from sqlalchemy.exc import SQLAlchemyError

from colandr.extensions import db


bp = Blueprint("errors", __name__)


@bp.app_errorhandler(Exception)
def handle_error(error):
    current_app.logger.error(str(error))
    return (jsonify({'errors': str(error)}), 500)

@bp.app_errorhandler(SQLAlchemyError)
def handle_sqlalchemy_error(error):
    current_app.logger.error('db unable to handle request! rolling back...')
    db.session.rollback()
    db.session.remove()
    return (jsonify({'errors': str(error)}), 500)

@bp.app_errorhandler(422)
def handle_validation_error(error):
    return (jsonify({'errors': error.exc.messages}), 422)
