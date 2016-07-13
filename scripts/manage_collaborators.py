#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import sys

import cipy

LOGGER = logging.getLogger('manage_collaborators')
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


def get_user_ids_from_emails(emails, users_db):
    query = "SELECT user_id FROM users WHERE email = %(email)s"
    user_ids = []
    for email in emails:
        try:
            user_id = list(users_db.run_query(query, {'email': email}))[0]['user_id']
        except IndexError:
            msg = 'user email "{}" not found in db'.format(email)
            raise ValueError(msg)
        user_ids.append(user_id)
    return user_ids


def main():
    parser = argparse.ArgumentParser(
        description='Invite collaborators to an existing systematic review project.')
    parser.add_argument(
        '--owner_user_id', type=int, required=True, metavar='owner_user_id',
        help='unique identifier of current user and owner of review')
    parser.add_argument(
        '--review_id', type=int, required=True, metavar='review_id',
        help='unique identifier of current systematic map review')
    parser.add_argument(
        '--add_user_emails', type=str, nargs='+', metavar='add_user_emails',
        help='email(s) of user(s) to add as collaborators on review')
    parser.add_argument(
        '--remove_user_emails', type=str, nargs='+', metavar='remove_user_emails',
        help='email(s) of user(s) to remove as collaborators on review')
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
        args.owner_user_id, args.review_id, reviews_db)

    if args.add_user_emails:
        add_user_ids = get_user_ids_from_emails(args.add_user_emails, users_db)
        for user_id in add_user_ids:
            reviews_db.execute(
                reviews_db.ddl['templates']['add_collaborator'],
                {'review_id': args.review_id, 'owner_user_id': owner_user_id, 'user_id': user_id},
                act=act)
            users_db.execute(
                users_db.ddl['templates']['add_review'],
                {'review_id': args.review_id, 'user_id': user_id},
                act=act)
            LOGGER.info('user id=%s added as collaborator to review id=%s %s',
                        user_id, args.review_id, '' if act is True else '(TEST)')

    if args.remove_user_emails:
        remove_user_ids = get_user_ids_from_emails(args.remove_user_emails, users_db)
        # sanity check!
        if any(user_id == owner_user_id for user_id in remove_user_ids):
            msg = "review owner id={} can't be removed as collaborator".format(owner_user_id)
            raise ValueError(msg)
        for user_id in remove_user_ids:
            reviews_db.execute(
                reviews_db.ddl['templates']['remove_collaborator'],
                {'review_id': args.review_id, 'owner_user_id': owner_user_id, 'user_id': user_id},
                act=act)
            users_db.execute(
                users_db.ddl['templates']['remove_review'],
                {'review_id': args.review_id, 'user_id': user_id},
                act=act)
            LOGGER.info('user id=%s removed as collaborator to review id=%s %s',
                        user_id, args.review_id, '' if act is True else '(TEST)')


if __name__ == '__main__':
    sys.exit(main())
