#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('create_project')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)

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
    projects_db = cipy.db.PostgresDB(conn_creds, ddl='projects')
    projects_db.create_table(act=act)

    name = input('Enter project name: ')
    description = input('Enter project description (optional): ')
    creator_user_id = args.user_id
    user_ids = [args.user_id]

    record = {'name': name,
              'description': description,
              'creator_user_id': creator_user_id,
              'user_ids': user_ids}
    sanitized_record = cipy.validation.project.sanitize(record)
    project = cipy.validation.project.Project(sanitized_record)
    try:
        project.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_record)
        LOGGER.exception(msg)

    validated_record = project.to_primitive()

    if act is True:
        projects_db.insert_values(
            validated_record, columns=list(sanitized_record.keys()), act=act)
    else:
        msg = 'valid record: {}'.format(validated_record)
        LOGGER.info(msg)


if __name__ == '__main__':
    sys.exit(main())
