from flask import render_template
from app import app
import io
import os
from pprint import pprint

import requests

sess = requests.session()

def call_endpoint(method, endpoint,
                  auth=None, verbose=True, return_json=True, **kwargs):
    url = BASE_URL + endpoint
    response = requests.request(method, url, auth=auth, **kwargs)

    if verbose is True:
        print(method, '=>', response.url)
    if return_json is True:
        return response.json()
    else:
        return response


def get_auth_token(email, password):
    return (call_endpoint('authtoken', 'get', (email, password))['token'], '')

# TODO: find a way to not have hard-coded urls/creds here, this seems bad!
BASE_URL = 'http://localhost:5001/'

login_creds = ('burtondewilde@gmail.com', 'password')

response = call_endpoint('GET', 'authtoken', auth=login_creds)
auth = (response['token'], '')

user_id = 1
def call_user():
    return
    # user_id += 1


reviews = call_endpoint('GET', 'reviews', auth=auth)

citation_id = 1

citation = call_endpoint('GET', 'citations/{id}'.format(id=citation_id),
             params={'fields': None},
             auth=auth)

citations = call_endpoint('GET', 'citations',
             params={'review_id': 1,'per_page': 10},
             auth=auth)

user = call_user()
print ('///////HERE////////')
# print (call_endpoint('GET', 'users/{id}'.format(id=1), auth=auth))
call_endpoint('GET', 'reviews/{id}'.format(id=1), auth=auth)
print (reviews)
print ('///////////////')

@app.route('/')
# @app.route('/index')
@app.route('/citation_screening')

# def index():
#     return render_template("index.html",
#                            user=call_endpoint('GET', 'users/{id}'.format(id=1), auth=auth),
#                            review_list=call_endpoint('GET', 'reviews', auth=auth)
#                            )
def citation_screening():
    return render_template("citation_screening.html",
                           citations=citations
                           )
