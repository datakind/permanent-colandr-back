import typing as t

import webargs.core
import webargs.flaskparser
from flask import current_app
from werkzeug import exceptions
from werkzeug.http import HTTP_STATUS_CODES

from .api_v1 import api as api_v1


@api_v1.errorhandler(exceptions.HTTPException)
def http_error(error):
    message = error.description
    current_app.logger.exception(message)
    return _make_error_response(error.code, message)


@api_v1.errorhandler(exceptions.BadRequest)
def bad_request_error(error):
    message = str(error)
    current_app.logger.error(message)
    return _make_error_response(400, message)


@api_v1.errorhandler(exceptions.Unauthorized)
def unauthorized_error(error):
    message = str(error)
    current_app.logger.error(message)
    return _make_error_response(401, message)


@api_v1.errorhandler(exceptions.Forbidden)
def forbidden_error(error):
    message = str(error)
    current_app.logger.error(message)
    return _make_error_response(403, message)


@api_v1.errorhandler(exceptions.NotFound)
def not_found_error(error):
    message = str(error)
    current_app.logger.error(message)
    return _make_error_response(404, message)


@api_v1.errorhandler(exceptions.InternalServerError)
def internal_server_error(error):
    """See also: :func:`colandr.errors.handle_error()"""
    message = str(error)
    current_app.logger.exception(message)
    return _make_error_response(500, message)


@webargs.flaskparser.parser.error_handler
def validation_error(error, req, schema, *, error_status_code, error_headers):
    """
    Handle validation errors during parsing. Aborts the current HTTP request and
    responds with a 422 error.

    This error handler is necessary for using webargs with Flask-RESTX.
    See: webargs/issues/181
    """
    status_code = error_status_code or webargs.core.DEFAULT_VALIDATION_STATUS
    webargs.flaskparser.abort(status_code, exc=error, messages=error.messages)


def _make_error_response(
    status_code: int, message: t.Optional[str] = None
) -> tuple[dict[str, str], int]:
    data = {"error": HTTP_STATUS_CODES.get(status_code, "Unknown error")}
    if message:
        data["message"] = message
    return (data, status_code)


# TODO: do we need this?
# @api_v1.errorhandler
# def default_error(error):
#     message = f"an unhandled exception occurred: {error}"
#     current_app.logger.exception(message)
#     response = jsonify({"message": message})
#     response.status_code = getattr(error, "code", 500)
#     return response
