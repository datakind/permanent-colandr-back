#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

import cipy

LOGGER = logging.getLogger('delete_project')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def get_owned_projects(user_id, projects_db):
    query = """
    SELECT project_id, name, created_ts
    FROM projects
    WHERE owner_user_id = %(user_id)s
    """
    owned_projects = list(projects_db.run_query(
        query, bindings={'user_id': user_id}))
    return owned_projects


def delete_owned_projects(project_ids, user_id, projects_db, act):
    for project_id in project_ids:
        projects_db.execute(
            projects_db.ddl['templates']['delete_project'],
            {'project_id': project_id, 'user_id': user_id},
            act=act)
        LOGGER.info('deleted owned project id=%s %s',
                    project_id, '' if act is True else '(TEST)')


def remove_deleted_user_from_projects(user_id, projects_db, act):
    modified_projects = projects_db.run_query(
        projects_db.ddl['template']['remove_deleted_user'],
        {'user_id': user_id},
        act=act)
    if act is True:
        list(modified_projects)


def main():
    parser = argparse.ArgumentParser(
        description='Delete an existing user.')
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

    # delete owned projects, or bail out
    owned_projects = get_owned_projects(args.user_id, projects_db)
    if owned_projects:
        msg_lines = [op['name'] + '(' + op['created_ts'] + ')'
                     for op in owned_projects]
        msg = 'The following owned projects will also be deleted:\n{}'.format(
            '\n'.join(msg_lines))
        LOGGER.warning(msg)
        choice = input('Continue anyway (y/n)? ')
        if choice == 'y':
            delete_owned_projects(
                [op['project_id'] for op in owned_projects],
                args.user_id, projects_db, act)
        elif choice == 'n':
            LOGGER.info('Okay! user id=%s not deleted', args.user_id)
            return
        else:
            raise ValueError('invalid input: "{}"'.format(choice))

    # remove user from associated projects
    updated_projects = projects_db.run_query(
        projects_db.ddl['templates']['remove_deleted_user'],
        {'user_id': args.user_id},
        act=act)
    if act is True:
        updated_project_ids = [project['project_id'] for project in updated_projects]
        LOGGER.info('user id=%s removed from project ids=%s',
                    args.user_id, updated_project_ids)
    else:
        LOGGER.info('deleted user id=%s from projects (TEST)', args.user_id)

    # delete user from users table
    users_db.execute(
        users_db.ddl['templates']['delete_user'],
        {'user_id': args.user_id},
        act=act)
    LOGGER.info('deleted user id=%s %s',
                args.user_id, '' if act is True else '(TEST)')


if __name__ == '__main__':
    sys.exit(main())
