#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

import cipy

LOGGER = logging.getLogger('delete_review')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def verify_user_is_review_owner(user_id, review_id, reviews_db):
    try:
        owner_user_id = list(reviews_db.run_query(
            reviews_db.ddl['templates']['get_owner_user_id'],
            {'review_id': review_id},
            act=True))[0]['owner_user_id']
    except IndexError:
        msg = 'review id={} not found'.format(review_id)
        LOGGER.error(msg)
        raise ValueError(msg)
    if owner_user_id != user_id:
        msg = 'user id={} is not owner of review id={}; unable to delete'.format(
            user_id, review_id)
        raise ValueError(msg)
    return owner_user_id


def main():
    parser = argparse.ArgumentParser(
        description='Delete an existing systematic map review.')
    parser.add_argument(
        '--user_id', type=int, required=True, metavar='user_id',
        help='unique identifier of current user')
    parser.add_argument(
        '--review_id', type=int, required=True, metavar='review_id',
        help='unique identifier of current systematic map review')
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

    owner_user_id = verify_user_is_review_owner(
        args.user_id, args.review_id, reviews_db)

    # delete review from reviews table
    reviews_db.execute(
        reviews_db.ddl['templates']['delete_review'],
        {'review_id': args.review_id, 'owner_user_id': owner_user_id},
        act=act)

    # remove review from associated users in users table
    updated_users = users_db.run_query(
        users_db.ddl['templates']['remove_deleted_review'],
        {'review_id': args.review_id},
        act=act)

    if act is True:
        updated_user_ids = [user['user_id'] for user in updated_users]
        LOGGER.info('review id=%s removed from user ids=%s',
                    args.review_id, updated_user_ids)
    else:
        LOGGER.info('deleted review id=%s (TEST)', args.review_id)


if __name__ == '__main__':
    sys.exit(main())
