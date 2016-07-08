#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('create_project')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def get_project_info(user_id):
    name = input('Enter project name: ')
    description = input('Enter project description (optional): ')
    owner_user_id = user_id
    user_ids = [user_id]
    return {'name': name,
            'description': description,
            'owner_user_id': owner_user_id,
            'user_ids': user_ids}


def sanitize_and_validate_project_info(project_info):
    sanitized_project_info = cipy.validation.project.sanitize(project_info)
    project = cipy.validation.project.Project(sanitized_project_info)
    try:
        project.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_project_info)
        LOGGER.exception(msg)
    return project.to_primitive()


def main():
    parser = argparse.ArgumentParser(
        description='Create a new systematic map project.')
    parser.add_argument(
        '--user_id', type=int, required=True, metavar='user_id',
        help='unique identifier of current user')
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
    projects_db = cipy.db.PostgresDB(conn_creds, ddl='projects')
    projects_db.create_table(act=act)

    project_info = get_project_info(args.user_id)
    validated_project_info = sanitize_and_validate_project_info(project_info)

    if act is True:
        # add project to projects table
        created_project_id = list(projects_db.run_query(
            projects_db.ddl['templates']['create_project'],
            validated_project_info,
            act=act))[0]['project_id']
        # update owner user in users table
        updated_user_id = list(users_db.run_query(
            users_db.ddl['templates']['add_created_project'],
            {'project_id': created_project_id, 'user_id': args.user_id},
            act=act))[0]['user_id']
        assert updated_user_id == args.user_id
        LOGGER.info('created project id=%s: %s',
            created_project_id, validated_project_info)
    else:
        LOGGER.info('created project (TEST): %s', validated_project_info)


if __name__ == '__main__':
    sys.exit(main())
