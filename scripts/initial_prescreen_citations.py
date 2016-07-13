#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import warnings
import sys

import pandas as pd

import cipy

LOGGER = logging.getLogger('initial_prescreen_citations')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def main():
    parser = argparse.ArgumentParser(
        description='Pre-screen citation records!')
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
    prescreening_db = cipy.db.PostgresDB(conn_creds, ddl='prescreening')
    prescreening_db.create_table(act=act)

    query = """
    SELECT COUNT(1) AS n
    FROM prescreening
    WHERE review_id = %(review_id)s
    """

    count = list(prescreening_db.run_query(query, {'review_id': args.review_id}))[0]['n']
    if count > 0:
        msg = 'review {} already has {} pre-screened citations'.format(
            args.review_id, count)
        warnings.warn(msg, UserWarning)

    n_iter = 0
    n_include = 0
    n_exclude = 0

    while n_include < 10 and n_exclude < 10:

        results = prescreening_db.run_query(
            cipy.db.queries.GET_CITATION_TEXTS_SAMPLE,
            bindings={'review_id': args.review_id})
        df = pd.DataFrame(results)

        break


if __name__ == '__main__':
    sys.exit(main())
