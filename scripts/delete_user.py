#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

import cipy

LOGGER = logging.getLogger('delete_user')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def get_owned_reviews(user_id, reviews_db):
    query = """
    SELECT review_id, name, created_ts
    FROM reviews
    WHERE owner_user_id = %(user_id)s
    """
    owned_reviews = list(reviews_db.run_query(
        query, bindings={'user_id': user_id}))
    return owned_reviews


def delete_owned_reviews(review_ids, user_id, reviews_db, act):
    for review_id in review_ids:
        reviews_db.execute(
            reviews_db.ddl['templates']['delete_review'],
            {'review_id': review_id, 'owner_user_id': user_id},
            act=act)
        LOGGER.info('deleted owned review id=%s %s',
                    review_id, '' if act is True else '(TEST)')


def remove_deleted_user_from_reviews(user_id, reviews_db, act):
    modified_reviews = reviews_db.run_query(
        reviews_db.ddl['template']['remove_deleted_user'],
        {'user_id': user_id},
        act=act)
    if act is True:
        list(modified_reviews)


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
    reviews_db = cipy.db.PostgresDB(conn_creds, ddl='reviews')

    # delete owned reviews, or bail out
    owned_reviews = get_owned_reviews(args.user_id, reviews_db)
    if owned_reviews:
        msg_lines = [review['name'] + ' (' + review['created_ts'].strftime('%Y-%m-%d') + ')'
                     for review in owned_reviews]
        msg = 'The following owned reviews will also be deleted:\n{}'.format(
            '\n'.join(msg_lines))
        LOGGER.warning(msg)
        choice = input('Continue anyway (y/n)? ')
        if choice == 'y':
            delete_owned_reviews(
                [op['review_id'] for op in owned_reviews],
                args.user_id, reviews_db, act)
        elif choice == 'n':
            LOGGER.info('Okay! user id=%s not deleted', args.user_id)
            return
        else:
            raise ValueError('invalid input: "{}"'.format(choice))

    # remove user from associated reviews
    updated_reviews = reviews_db.run_query(
        reviews_db.ddl['templates']['remove_deleted_user'],
        {'user_id': args.user_id},
        act=act)
    if act is True:
        updated_review_ids = [review['review_id'] for review in updated_reviews]
        LOGGER.info('user id=%s removed from review ids=%s',
                    args.user_id, updated_review_ids)
    else:
        LOGGER.info('deleted user id=%s from reviews (TEST)', args.user_id)

    # delete user from users table
    users_db.execute(
        users_db.ddl['templates']['delete_user'],
        {'user_id': args.user_id},
        act=act)
    LOGGER.info('deleted user id=%s %s',
                args.user_id, '' if act is True else '(TEST)')


if __name__ == '__main__':
    sys.exit(main())
