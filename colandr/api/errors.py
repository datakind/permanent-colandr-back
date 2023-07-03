import webargs.core
import webargs.flaskparser
from flask import current_app, jsonify
from flask_restx import Namespace
from werkzeug import exceptions


ns = Namespace("errors")


@ns.errorhandler
def default_error(err):
    message = "an unhandled exception occurred: {}".format(err)
    current_app.logger.error(message)
    response = jsonify({"message": message})
    response.status_code = 500
    return response


@ns.errorhandler(exceptions.BadRequest)
def bad_request_error(err):
    message = "{}".format(err)
    current_app.logger.error(message)
    response = jsonify({"message": message})
    response.status_code = 400
    return response


@ns.errorhandler(exceptions.Unauthorized)
def unauthorized_error(err):
    message = "{}".format(err)
    current_app.logger.error(message)
    response = jsonify({"message": message})
    response.status_code = 401
    return response


@ns.errorhandler(exceptions.Forbidden)
def forbidden_error(err):
    message = "{}".format(err)
    current_app.logger.error(message)
    response = jsonify({"message": message})
    response.status_code = 403
    return response


@ns.errorhandler(exceptions.NotFound)
def not_found_error(err):
    message = "{}".format(err)
    current_app.logger.error(message)
    response = jsonify({"message": message})
    response.status_code = 404
    return response


@ns.errorhandler(exceptions.InternalServerError)
def internal_server_error(err):
    message = "{}".format(err)
    current_app.logger.error(message)
    response = jsonify({"message": message})
    response.status_code = 500
    return response


@webargs.flaskparser.parser.error_handler
def validation_error(error, req, schema, error_status_code, error_headers):
    """
    Handle validation errors during parsing. Aborts the current HTTP request and
    responds with a 422 error.

    This error handler is necessary for using webargs with Flask-RESTX.
    See: webargs/issues/181
    """
    status_code = error_status_code or webargs.core.DEFAULT_VALIDATION_STATUS
    webargs.flaskparser.abort(
        status_code,
        exc=error,
        messages=error.messages,
    )


def db_integrity_error(message):
    response = jsonify({"message": message})
    response.status_code = 422
    return response
