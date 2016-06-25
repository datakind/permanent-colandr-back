#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import csv
import io
import logging
import os
import sys
import tempfile

import psycopg2

import cipy

LOGGER = logging.getLogger('dedupe_records')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)


def get_candidate_dupes(citation_db, project_id):
    """
    Args:
        citations_db (cipy.db.PostgresDB)
        project_id (int)

    Yields:
        list[tuple]
    """
    results = citation_db.run_query(cipy.db.queries.GET_CANDIDATE_DUPE_CLUSTERS,
                                    {'project_id': project_id})

    block_id = None
    records = []
    for row in results:
        if row['block_id'] != block_id:
            if records:
                yield records

            block_id = row['block_id']
            records = []

        smaller_ids = row['smaller_ids']
        if smaller_ids:
            smaller_ids = set(smaller_ids.split(','))
        else:
            smaller_ids = set()

        records.append((row['citation_id'],
                        cipy.db.make_immutable(row),
                        smaller_ids))

    if records:
        yield records


def main():
    parser = argparse.ArgumentParser(
        description='De-duplicate citation records!')
    parser.add_argument(
        '--project_id', type=int, required=True, metavar='project_id',
        help='unique identifier of current systematic map project')
    parser.add_argument(
        '--settings', type=str, required=True, metavar='settings_file_path',
        help='path to file on disk where dedupe model settings are saved')
    parser.add_argument(
        '--ddls', type=str, metavar='psql_ddls_dir', default=cipy.db.DEFAULT_DDLS_PATH,
        help='path to directory on disk where DDL files are saved')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    parser.add_argument(
        '--threshold', type=str, metavar='dedupe_score_threshold', default='auto',
        help="""float value in [0.0, 1.0] above which duplicates are automatically
        assigned; if 'auto' (default), an ideal value will be computed from data""")
    parser.add_argument(
        '--dryrun', action='store_true', default=False,
        help='flag to run script without modifying any data or models')
    args = parser.parse_args()

    conn_creds = cipy.db.get_conn_creds(args.database_url)

    citations_ddl = cipy.db.get_ddl('citations', ddls_path=args.ddls)
    citations_db = cipy.db.PostgresDB(conn_creds, citations_ddl)
    duplicates_ddl = cipy.db.get_ddl('duplicates', ddls_path=args.ddls)
    duplicates_db = cipy.db.PostgresDB(conn_creds, duplicates_ddl)

    duplicates_db.create_table()
    with duplicates_db.conn.cursor() as cur:
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS duplicates_canonical_citation_id_idx
            ON duplicates (canonical_citation_id)
            """)

    LOGGER.info('reading dedupe settings from %s', args.settings)
    deduper = cipy.db.get_deduper(args.settings, num_cores=2)

    if args.threshold == 'auto':
        results = citations_db.run_query(
            cipy.db.queries.GET_SAMPLE_FOR_DUPE_THRESHOLD,
            {'project_id': args.project_id})
        dupe_threshold = deduper.threshold(
            {row['citation_id']: cipy.db.make_immutable(row) for row in results},
            recall_weight=0.5)
    else:
        dupe_threshold = float(args.threshold)
        if dupe_threshold < 0 or dupe_threshold > 1:
            msg = "dupe threshold '{}' invalid, must be in [0.0, 1.0]".format(
                dupe_threshold)
            raise ValueError(msg)

    LOGGER.info('duplicate threshold = %s', dupe_threshold)

    clustered_dupes = deduper.matchBlocks(
        get_candidate_dupes(citations_db, args.project_id),
        threshold=dupe_threshold)
    LOGGER.info('found %s duplicate clusters', len(clustered_dupes))

    csv_file = tempfile.NamedTemporaryFile(
        prefix='duplicates_', delete=False, mode='wt')
    csv_writer = csv.writer(csv_file)

    n_records = 0
    for cids, scores in clustered_dupes:
        citation_duplicate_scores = {cid: score
                                     for cid, score in zip(cids, scores)}
        canonical_citation = citations_db.run_query(
            cipy.db.queries.GET_DUPE_CLUSTER_CANONICAL_ID,
            {'project_id': args.project_id,
            'citation_ids': tuple(int(cid) for cid in cids)})
        canonical_citation_id = tuple(canonical_citation)[0]['citation_id']

        for citation_id, duplicate_score in citation_duplicate_scores.items():
            n_records += 1
            csv_writer.writerow(
                (citation_id, args.project_id, canonical_citation_id,
                 duplicate_score, False, None))

    csv_file.close()

    try:
        with io.open(csv_file.name, mode='rt') as f:
            with duplicates_db.conn.cursor() as cur:
                cur.copy_expert('COPY duplicates FROM STDIN CSV', f)
        LOGGER.info('inserted %s records into %s db',
                    n_records, duplicates_db.ddl['table_name'])
    except psycopg2.DataError:
        LOGGER.exception()

    os.remove(csv_file.name)


if __name__ == '__main__':
    sys.exit(main())
