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

    LOGGER.info('blocking...')

    # To run blocking on such a large set of data, we create a separate table
    # that contains blocking keys and record ids
    LOGGER.info('creating blocking_map database...')

    with citations_db.conn.cursor() as cur:
        cur.execute('DROP TABLE IF EXISTS dedupe_blocking_map')
        cur.execute(
            """
            CREATE TABLE dedupe_blocking_map
            (block_key VARCHAR NOT NULL, citation_id INTEGER NOT NULL)
            """)

    # If dedupe learned an Index Predicate, we have to take a pass through
    # the data and create indices

    for field in deduper.blocker.index_fields:
        query = 'SELECT DISTINCT {col} FROM {table}'.format(
            col=field, table=citations_db.ddl['table_name'])
        print(query)
        results = citations_db.run_query(query)

        field_type = [column['type'] for column in citations_db.ddl['columns']
                      if column['name'] == field][0]
        if 'array' in field_type.lower():
            field_data = (tuple(row[field]) for row in results
                          if row and row.get(field))
        else:
            field_data = (row[field] for row in results if row)
        deduper.blocker.index(field_data, field)

    # Now we are ready to write our blocking map table by creating a generator
    # that yields unique (block_key, citation_id) tuples

    data = ((row['citation_id'], cipy.db.make_immutable(row))
            for row in citations_db.run_query(
                citations_db.ddl['templates']['select_citations_basic_info']))
    b_data = deduper.blocker(data)

    # Write out blocking map to CSV so we can quickly load in with Postgres COPY

    csv_file = tempfile.NamedTemporaryFile(prefix='blocks_',
                                           delete=False,
                                           mode='wt')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerows(b_data)
    csv_file.close()

    try:
        with io.open(csv_file.name, mode='rt') as f:
            with citations_db.conn.cursor() as cur:
                cur.copy_expert('COPY dedupe_blocking_map FROM STDIN CSV', f)
    except psycopg2.DataError:
        LOGGER.exception()

    os.remove(csv_file.name)

    # Remove blocks that contain only one record, sort by block key and citation
    # key and index blocking map

    LOGGER.info('preparing blocking table...')
    with citations_db.conn.cursor() as cur:
        cur.execute(
            """
            CREATE INDEX dedupe_blocking_map_key_idx
            ON dedupe_blocking_map (block_key)
            """)

    with citations_db.conn.cursor() as cur:

        cur.execute('DROP TABLE IF EXISTS dedupe_plural_key')
        cur.execute('DROP TABLE IF EXISTS dedupe_plural_block')
        cur.execute('DROP TABLE IF EXISTS dedupe_covered_blocks')
        cur.execute('DROP TABLE IF EXISTS dedupe_smaller_coverage')

        # Many block_keys will only form blocks that contain a single record
        # Since there are no comparisons possible withing such a singleton block
        # we can ignore them

        LOGGER.info("calculating plural_key...")
        cur.execute(
            """
            CREATE TABLE dedupe_plural_key
            (block_key VARCHAR, block_id SERIAL PRIMARY KEY)
            """)
        cur.execute(
            """
            INSERT INTO dedupe_plural_key (block_key)
            SELECT block_key FROM dedupe_blocking_map
            GROUP BY block_key HAVING COUNT(*) > 1
            """)

        LOGGER.info('creating block_key index...')
        cur.execute(
            """
            CREATE UNIQUE INDEX dedupe_block_key_idx
            ON dedupe_plural_key (block_key)
            """)

        LOGGER.info("calculating plural_block...")
        cur.execute(
            """
            CREATE TABLE dedupe_plural_block
            AS (SELECT t1.block_id, t2.citation_id
                FROM dedupe_plural_key AS t1, dedupe_blocking_map AS t2
                WHERE t1.block_key = t2.block_key)
            """)

        LOGGER.info('adding citation_id index and sorting index...')
        cur.execute(
            """
            CREATE INDEX dedupe_plural_block_citation_id_idx
            ON dedupe_plural_block (citation_id)
            """)
        cur.execute(
            """
            CREATE UNIQUE INDEX dedupe_plural_block_block_id_citation_id_uniq
            ON dedupe_plural_block (block_id, citation_id)
            """)

        # To use Kolb, et. al's Redundant Free Comparison scheme, we need to
        # keep track of all the block_ids that are associated with particular
        # citation records

        LOGGER.info('creating covered_blocks...')
        cur.execute(
            """
            CREATE TABLE dedupe_covered_blocks AS
                (SELECT
                     citation_id,
                     string_agg(CAST(block_id AS TEXT), ',' ORDER BY block_id) AS sorted_ids
                 FROM dedupe_plural_block
                 GROUP BY citation_id)
            """)
        cur.execute(
            """
            CREATE UNIQUE INDEX dedupe_covered_blocks_citation_id_idx
            ON dedupe_covered_blocks (citation_id)
            """)

        # For every block of records, we need to keep track of a citation records's
        # associated block_ids that are SMALLER than the current block's id

        LOGGER.info("creating smaller_coverage...")
        cur.execute(
            """
            CREATE TABLE dedupe_smaller_coverage AS
                (SELECT
                     citation_id,
                     block_id,
                     TRIM(',' FROM split_part(sorted_ids, CAST(block_id AS TEXT), 1)) AS smaller_ids
                 FROM dedupe_plural_block
                 INNER JOIN dedupe_covered_blocks
                 USING (citation_id))
            """)


if __name__ == '__main__':
    sys.exit(main())
