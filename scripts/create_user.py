#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import getpass
import logging
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('create_user')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def get_user_info():
    name = input('Enter user name: ')
    email = input('Enter user email: ')
    email_confirm = input('Confirm user email: ')
    while email != email_confirm:
        LOGGER.warning('email mismatch, please try again...')
        email = input('Enter user email: ')
        email_confirm = input('Confirm user email: ')
    password = getpass.getpass(prompt='Enter password: ')
    password_confirm = getpass.getpass(prompt='Confirm password: ')
    while password != password_confirm:
        LOGGER.warning('password mismatch, please try again...')
        password = getpass.getpass(prompt='Enter password: ')
        password_confirm = getpass.getpass(prompt='Confirm password: ')

    return {'name': name, 'email': email, 'password': password}


def sanitize_and_validate_user_info(user_info):
    sanitized_user_info = cipy.validation.user.sanitize(user_info)
    user = cipy.validation.user.User(sanitized_user_info)
    try:
        user.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_user_info)
        LOGGER.exception(msg)
    return user.to_primitive()


def check_if_email_exists(users_db, email):
    check = list(users_db.run_query(
        users_db.ddl['templates']['check_email_exists'],
        bindings={'email': email}))
    if check:
        msg = 'user with email "{}" already exists'.format(email)
        raise ValueError(msg)


def main():
    parser = argparse.ArgumentParser(
        description='Create a new app user.')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='flag to run script without modifying any data or models')
    args = parser.parse_args()

    act = not args.test

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    users_db = cipy.db.PostgresDB(conn_creds, ddl='users')
    users_db.create_table(act=act)

    user_info = get_user_info()
    validated_user_info = sanitize_and_validate_user_info(user_info)

    # add new user to db if email not already used, or just log output
    if act is True:
        check_if_email_exists(users_db, validated_user_info['email'])
        users_db.execute(
            users_db.ddl['templates']['insert_values'],
            bindings=validated_user_info, act=act)
    else:
        msg = 'valid user: {}'.format(validated_user_info)
        LOGGER.info(msg)


if __name__ == '__main__':
    sys.exit(main())
