#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import csv
import io
import logging
import os
import sys
import tempfile
import warnings

import dedupe
import psycopg2

import cipy

LOGGER = logging.getLogger('train_deduper')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def main():
    parser = argparse.ArgumentParser(
        description="""Train a model to deduplicate citation records.""")
    parser.add_argument(
        '--settings', type=str, required=True, metavar='settings_file_path',
        help='path to file on disk where dedupe model settings are saved')
    parser.add_argument(
        '--training', type=str, required=True, metavar='training_file_path')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    parser.add_argument(
        '--update', action='store_true', default=False)
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='flag to run script without modifying any data or models')
    args = parser.parse_args()

    act = not args.test

    # HACK!
    if args.update is True:
        warnings.warn(
            'updating a trained dedupe model does not appear to work', UserWarning)

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    citations_db = cipy.db.PostgresDB(conn_creds, ddl='citations')

    if args.update is False and os.path.exists(args.settings):
        LOGGER.info('reading dedupe settings from %s', args.settings)
        deduper = cipy.db.get_deduper(args.settings, num_cores=2)

    else:
        variables = [
            {'field': 'authors', 'type': 'Set', 'has missing': True},
            {'field': 'title', 'type': 'String', 'has missing': True},
            {'field': 'abstract', 'type': 'Text', 'has missing': True},
            {'field': 'publication_year', 'type': 'Exact', 'has missing': True},
            {'field': 'doi', 'type': 'String', 'has missing': True}
        ]
        deduper = dedupe.Dedupe(variables, num_cores=2)

        data = {row['citation_id']: cipy.db.make_immutable(row)
                for row in citations_db.run_query(
                    citations_db.ddl['templates']['select_citations_basic_info'])}
        deduper.sample(data, 25000)

        if os.path.exists(args.training):
            LOGGER.info('reading labeled examples from %s', args.training)
            with io.open(args.training, mode='rt') as f:
                deduper.readTraining(f)

        LOGGER.info('starting active labeling...')
        dedupe.consoleLabel(deduper)

        if act is True:
            LOGGER.info('writing dedupe training data to %s', args.training)
            with io.open(args.training, mode='wt') as f:
                deduper.writeTraining(f)
        else:
            LOGGER.info('writing dedupe training data to %s (TEST)', args.training)

        deduper.train(maximum_comparisons=1000000, recall=0.95)

        if act is True:
            LOGGER.info('writing dedupe settings data to %s', args.settings)
            with io.open(args.settings, mode='wb') as f:
                deduper.writeSettings(f)
        else:
            LOGGER.info('writing dedupe settings data to %s (TEST)', args.settings)

        deduper.cleanupTraining()


if __name__ == '__main__':
    sys.exit(main())
