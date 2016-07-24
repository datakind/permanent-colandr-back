#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging

import cipy

LOGGER = logging.getLogger('screen_citations')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def main():
    parser = argparse.ArgumentParser(
        description='Screen citations for a systematic review.')
    parser.add_argument(
        '--user_id', type=int, required=True, metavar='user_id',
        help='unique identifier of current user')
    parser.add_argument(
        '--review_id', type=int, required=True, metavar='review_id',
        help='unique identifier of current systematic map review')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    # TODO: remove this argument
    parser.add_argument(
        '--auto', action='store_true', default=False,
        help='HACK: automatically fill in known selection decisions for CI\'s map')
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='flag to run script without modifying any data or models')
    args = parser.parse_args()

    act = not args.test

    if args.auto is True:
        selection_data = cipy.hacks.load_citation_selection_data()

    while n_include < 10 and n_exclude < 10:

        results = prescreening_db.run_query(
            cipy.db.queries.SELECT_CITATIONS_TO_SCREEN,
            bindings={'review_id': review_id, 'sample_size': 10000})
        df = pd.DataFrame(results)
