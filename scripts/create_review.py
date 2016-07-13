#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('create_review')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def get_review_info(user_id):
    name = input('Review name: ')
    description = input('Review description (optional):\n')
    owner_user_id = user_id
    user_ids = [user_id]
    return {'name': name,
            'description': description,
            'owner_user_id': owner_user_id,
            'user_ids': user_ids}


def sanitize_and_validate_review_info(review_info):
    sanitized_review_info = cipy.validation.review.sanitize(review_info)
    review = cipy.validation.review.Review(sanitized_review_info)
    try:
        review.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_review_info)
        LOGGER.exception(msg)
    return review.to_primitive()


def main():
    parser = argparse.ArgumentParser(
        description='Create a new systematic map review.')
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
    reviews_db = cipy.db.PostgresDB(conn_creds, ddl='reviews')
    reviews_db.create_table(act=act)

    review_info = get_review_info(args.user_id)
    validated_review_info = sanitize_and_validate_review_info(review_info)

    if act is True:
        # add review to reviews table
        created_review_id = list(reviews_db.run_query(
            reviews_db.ddl['templates']['create_review'],
            validated_review_info,
            act=act))[0]['review_id']
        # update owner user in users table
        updated_user_id = list(users_db.run_query(
            users_db.ddl['templates']['add_created_review'],
            {'review_id': created_review_id, 'user_id': args.user_id},
            act=act))[0]['user_id']
        assert updated_user_id == args.user_id
        LOGGER.info('created review id=%s: %s',
                    created_review_id, validated_review_info)
    else:
        LOGGER.info('created review (TEST): %s', validated_review_info)


if __name__ == '__main__':
    sys.exit(main())
