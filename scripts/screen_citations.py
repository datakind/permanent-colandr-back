#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import logging
import math
import time
import sys

import pandas as pd

import cipy

LOGGER = logging.getLogger('screen_citations')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def combine_citation_text(row):
    title = row['title'] or ''
    abstract = row['abstract'] or ''
    keywords = '; '.join(row['keywords']) if row['keywords'] else ''
    text = '\n\n'.join((title, abstract, keywords)).strip()
    return text


def get_keyterms_regex_match_score(citation_text, keyterms_regex):
    full_len = len(citation_text)
    if full_len == 0:
        return 0.0
    match_len = sum(
        len(match.group()) for match in keyterms_regex.finditer(citation_text))
    nonmatch_len = full_len - match_len
    try:
        return math.sqrt(full_len) * match_len / nonmatch_len
    except ValueError:
        LOGGER.exception('error: %s, %s, %s', match_len, nonmatch_len, full_len)
        return 0.0


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

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    pgdb = cipy.db.PostgresDB(conn_creds)
    status_db = cipy.db.PostgresDB(conn_creds, ddl='citation_status')

    if args.auto is True:
        selection_data = cipy.hacks.load_citation_selection_data()

    status_counts = status_db.run_query(
        status_db.ddl['templates']['select_citation_screening_status_counts'],
        {'review_id': args.review_id})
    status_counts = {item['citation_screening_status']: item['count']
                     for item in status_counts}
    n_included = status_counts.get('included', 0)
    n_excluded = status_counts.get('excluded', 0)

    LOGGER.info('%s citations included, %s citations excluded', n_included, n_excluded)

    if n_included < 10 and n_excluded < 10:
        # get review keyterms and build regex
        query = "SELECT keyterms FROM review_plans WHERE review_id = %(review_id)s"
        keyterms = list(pgdb.run_query(query, {'review_id': args.review_id}))
        if keyterms:
            keyterms = keyterms[0]['keyterms']
            keyterms_regex = cipy.utils.get_keyterms_regex(keyterms)
        else:
            raise ValueError('review does not have any keyterms assigned yet')

        # download a sample of citations and their texts for regex matching
        results = pgdb.run_query(
            cipy.db.queries.SELECT_CITATIONS_TO_SCREEN,
            bindings={'review_id': args.review_id, 'sample_size': 10000})
        df = pd.DataFrame(results)
        df['citation_text'] = df.apply(combine_citation_text, axis=1)

        df['regex_match_score'] = df['citation_text'].map(
            lambda x: get_keyterms_regex_match_score(x, keyterms_regex))
        df['regex_match_pctrank'] = df['regex_match_score'].rank(pct=True, ascending=True)
        df.sort_values('regex_match_pctrank', inplace=True, ascending=False)
        df.reset_index(drop=True, inplace=True)

        for idx, row in df.iterrows():
            if (row['citation_screening'] and
                    any(cs['screened_by'] == args.user_id
                        for cs in row['citation_screening'])):
                LOGGER.info('citation id=%s already screened by you!', row['citation_id'])
                continue

            cipy.utils.present_citation(row.to_dict())
            if args.auto is True:
                time.sleep(0.25)
                decision = 'y' if selection_data[row['citation_id']] is True else 'n'
                print('\nINCLUDE (y/n/u)?', decision)
            else:
                decision = input('\nINCLUDE (y/n/u)? ')

            if decision == 'y':
                n_included += 1
            elif decision == 'n':
                n_excluded += 1

            LOGGER.info('%s/10 included, %s/10 excluded', n_included, n_excluded)
            if n_included >= 10 and n_excluded >= 10:
                break


if __name__ == '__main__':
    sys.exit(main())
