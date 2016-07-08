#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('delete_project')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def verify_user_is_project_owner(user_id, project_id, projects_db):
    try:
        owner_user_id = list(projects_db.run_query(
            projects_db.ddl['templates']['get_owner_user_id'],
            {'project_id': project_id},
            act=True))[0]['owner_user_id']
    except IndexError:
        msg = 'project id={} not found'.format(project_id)
        LOGGER.error(msg)
        raise ValueError(msg)
    if owner_user_id != user_id:
        msg = 'user id={} is not owner of project id={}; unable to delete'.format(
            user_id, project_id)
        raise ValueError(msg)
    return owner_user_id


def main():
    parser = argparse.ArgumentParser(
        description='Delete an existing systematic map project.')
    parser.add_argument(
        '--user_id', type=int, required=True, metavar='user_id',
        help='unique identifier of current user')
    parser.add_argument(
        '--project_id', type=int, required=True, metavar='project_id',
        help='unique identifier of current systematic map project')
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

    if act is True:

        owner_user_id = verify_user_is_project_owner(
            args.user_id, args.project_id, projects_db)

        # delete project from projects table
        deleted_project_id = list(projects_db.run_query(
            projects_db.ddl['templates']['delete_project'],
            {'project_id': args.project_id, 'user_id': owner_user_id},
            act=True))[0]['project_id']

        # remove project from associated users in users table
        update_users = users_db.run_query(
            users_db.ddl['templates']['remove_deleted_project'],
            {'project_id': args.project_id},
            act=True)
        modified_user_ids = [user['user_id'] for user in update_users]
        LOGGER.info('project id=%s removed from users ids=%s',
                    deleted_project_id, modified_user_ids)

    else:
        LOGGER.info('deleted project id=%s (TEST)', args.project_id)


if __name__ == '__main__':
    sys.exit(main())
