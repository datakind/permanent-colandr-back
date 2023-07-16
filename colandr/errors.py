from flask import Blueprint, current_app, jsonify
from sqlalchemy.exc import SQLAlchemyError

from colandr.extensions import db


bp = Blueprint("errors", __name__)


@bp.app_errorhandler(Exception)
def handle_error(error):
    current_app.logger.exception(str(error))
    return (jsonify({"errors": str(error)}), 500)


@bp.app_errorhandler(SQLAlchemyError)
def handle_sqlalchemy_error(error):
    current_app.logger.exception("unexpected db error: %s\nrolling back ...", error)
    db.session.rollback()
    db.session.remove()
    return (jsonify({"errors": str(error)}), 500)


@bp.app_errorhandler(422)
def handle_validation_error(error):
    headers = error.data.get("headers", None)
    messages = error.data.get("messages", ["Invalid request."])
    if headers:
        return (jsonify({"errors": messages}), error.code, headers)
    else:
        return (jsonify({"errors": messages}), error.code)


# TODO: figure out if we want/need this -- it's from the 1.0 version of colandr
# @bp.teardown_app_request
# def teardown_request(error):
#     if error:
#         current_app.logger.error(
#             "got server error while handling request! rolling back...\n%s", error
#         )
#         db.session.rollback()
#         db.session.remove()
#         return (jsonify({"errors": str(error)}), 500)
#     db.session.remove()
