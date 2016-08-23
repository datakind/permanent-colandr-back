import hug

from ciapi.hug_api.auth import AUTH
from ciapi.hug_api import citation
from ciapi.hug_api import citations
from ciapi.hug_api import user


@hug.get('/login', requires=AUTH)
def root():
    return True


@hug.request_middleware()
def process_data(request, response):
    response.set_header('Content-Type', 'application/vnd.api+json')


@hug.extend_api('/citations')
def get_citations():
    return [citations]


@hug.extend_api('/citation')
def get_citation():
    return [citation]


@hug.extend_api('/user')
def get_user():
    return [user]
