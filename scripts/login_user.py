#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import getpass
import logging
import sys

import cipy

LOGGER = logging.getLogger('login_user')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def get_user_login_info():
    email = input('Enter email: ')
    password = getpass.getpass(prompt='Enter password: ')
    return {'email': email, 'password': password}


def get_matching_user(users_db, user_login_info):
    db_matches = list(users_db.run_query(
        users_db.ddl['templates']['user_login'],
        bindings=user_login_info))
    if not db_matches:
        raise ValueError('invalid email and/or password')
    else:
        assert len(db_matches) == 1
        return db_matches[0]


def main():
    parser = argparse.ArgumentParser(
        description='Log-in a user.')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    args = parser.parse_args()

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    users_db = cipy.db.PostgresDB(conn_creds, ddl='users')

    # manually enter user login info
    user_login_info = get_user_login_info()

    # check if matching user exists in db, log a welcome
    user = get_matching_user(users_db, user_login_info)
    LOGGER.info('Welcome, %s!\n%s', user['name'], user)


if __name__ == '__main__':
    sys.exit(main())
