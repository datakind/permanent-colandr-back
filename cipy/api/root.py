import hug

import cipy
from cipy.api.auth import AUTH
from cipy.api import citation
from cipy.api import user


@hug.get('/', requires=AUTH)
def root():
    return 'Hello, World!'


@hug.request_middleware()
def process_data(request, response):
    response.set_header('Content-Type', 'application/vnd.api+json')


@hug.extend_api('/citation')
def get_citation():
    return [citation]
    # return [cipy.api.citation]


@hug.extend_api('/user')
def get_user():
    return [user]
