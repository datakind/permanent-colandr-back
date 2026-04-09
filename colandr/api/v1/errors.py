import apiflask as af


class BadRequestError(af.HTTPError):
    status_code = 400


class UnauthorizedError(af.HTTPError):
    status_code = 401


class ForbiddenError(af.HTTPError):
    status_code = 403


class NotFoundError(af.HTTPError):
    status_code = 404
