from flask import jsonify


def bad_request(message):
    response = jsonify({'error': 'bad request', 'message': message})
    response.status_code = 400
    return response


def unauthorized(message):
    response = jsonify({'error': 'unauthorized', 'message': message})
    response.status_code = 401
    return response


def forbidden(message):
    response = jsonify({'error': 'forbidden', 'message': message})
    response.status_code = 403
    return response


def validation(message):
    response = jsonify({'error': 'validation', 'message': message})
    response.status_code = 422
    return response


def no_data_found(message):
    response = jsonify({'error': 'no data found', 'message': message})
    response.status_code = 404
    return response
