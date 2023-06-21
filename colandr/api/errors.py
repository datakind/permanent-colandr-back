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


def validation_error(message):
    response = jsonify({"message": message})
    response.status_code = 422
    return response


def db_integrity_error(message):
    response = jsonify({"message": message})
    response.status_code = 422
    return response
