from flask import Blueprint, current_app, jsonify
from sqlalchemy import exc as sa_exc

from colandr.extensions import db


bp = Blueprint("errors", __name__)


@bp.app_errorhandler(Exception)
def handle_error(error):
    current_app.logger.exception(str(error))
    return (jsonify({"error": "Internal Server Error", "message": str(error)}), 500)


@bp.app_errorhandler(sa_exc.SQLAlchemyError)
def handle_sqlalchemy_error(error):
    current_app.logger.exception(
        "unexpected database error: %s\nrolling back ...", error
    )
    db.session.rollback()
    db.session.remove()
    return (jsonify({"error": "Internal Server Error", "message": str(error)}), 500)


# TODO: revisit this when we finally get round to dealing with marshmallow+webargs
@bp.app_errorhandler(422)
def handle_validation_error(error):
    headers = error.data.get("headers", None)
    messages = error.data.get("messages", ["Invalid request."])
    if headers:
        return (jsonify({"errors": messages}), error.code, headers)
    else:
        return (jsonify({"errors": messages}), error.code)
