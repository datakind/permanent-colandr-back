#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import io
import logging
import os

import dedupe

import cipy

LOGGER = logging.getLogger('train_deduper')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="""Train a model to deduplicate citation records.""")
    parser.add_argument(
        '--ddl', required=True, type=str, metavar='psql_ddl_file_path')
    parser.add_argument(
        '--settings', required=True, type=str, metavar='settings_file_path')
    parser.add_argument(
        '--training', required=True, type=str, metavar='training_file_path')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL')
    parser.add_argument(
        '--update', action='store_true', default=False)
    parser.add_argument(
        '--dryrun', action='store_true', default=False)
    args = parser.parse_args()

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    pgdb = cipy.db.PostgresDB(args.ddl, conn_creds)

    if args.update is False and os.path.exists(args.settings):
        LOGGER.info('reading dedupe settings from %s', args.settings)
        with io.open(args.settings, mode='rb') as f:
            deduper = dedupe.StaticDedupe(f, num_cores=2)

    else:
        variables = [
            {'field': 'authors', 'type': 'Set', 'has missing': True},
            {'field': 'title', 'type': 'String', 'has missing': True},
            {'field': 'abstract', 'type': 'Text', 'has missing': True},
            {'field': 'publication_year', 'type': 'Exact', 'has missing': True},
            {'field': 'doi', 'type': 'String', 'has missing': True}
        ]
        deduper = dedupe.Dedupe(variables, num_cores=2)

        query = """
                SELECT record_id, authors, title, abstract, publication_year, doi
                FROM citations
                """
        data = {}
        for row in pgdb.run_query(query):
            data[row['record_id']] = {
                'authors': tuple(row['authors'] if row['authors'] else []),
                'title': row.get('title', None),
                'abstract': row.get('abstract', None),
                'publication_year': row.get('publication_year', None),
                'doi': row.get('doi', None)}
        deduper.sample(data, 25000)

        if os.path.exists(args.training):
            LOGGER.info('reading labeled examples from %s', args.training)
            with io.open(args.training, mode='rt') as f:
                deduper.readTraining(f)

        LOGGER.info('starting active labeling...')
        dedupe.consoleLabel(deduper)

        with io.open(args.training, mode='wt') as f:
            deduper.writeTraining(f)

        deduper.train(maximum_comparisons=1000000, recall=0.95)

        with io.open(args.settings, mode='wb') as f:
            deduper.writeSettings(f)

        deduper.cleanupTraining()
