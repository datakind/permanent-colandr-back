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
from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('dedupe_records')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)

CREATE_DEDUPE_BLOCKING_MAP = """
    CREATE TABLE IF NOT EXISTS dedupe_blocking_map
    (block_key VARCHAR NOT NULL, citation_id BIGINT NOT NULL, review_id INT NOT NULL)
    """
CREATE_DEDUPE_PLURAL_KEY = """
    CREATE TABLE IF NOT EXISTS dedupe_plural_key
    (block_key VARCHAR, block_id BIGSERIAL PRIMARY KEY, review_id INT NOT NULL)
    """
CREATE_DEDUPE_PLURAL_BLOCK = """
    CREATE TABLE IF NOT EXISTS dedupe_plural_block
    (block_id BIGINT, citation_id BIGINT, review_id INT)
    """
CREATE_DEDUPE_COVERED_BLOCKS = """
    CREATE TABLE IF NOT EXISTS dedupe_covered_blocks
    (citation_id BIGINT, review_id INT, sorted_ids TEXT)
    """
CREATE_DEDUPE_SMALLER_COVERAGE = """
    CREATE TABLE IF NOT EXISTS dedupe_smaller_coverage
    (citation_id BIGINT, review_id INT, block_id BIGINT, smaller_ids TEXT)
    """

DELETE_REVIEW_ROWS = """
    DELETE FROM {table} WHERE review_id = %(review_id)s
    """


def get_candidate_dupes(pgdb, review_id):
    """
    Args:
        pgdb (cipy.db.PostgresDB)
        review_id (int)

    Yields:
        list[tuple]
    """
    results = pgdb.run_query(
        cipy.db.queries.GET_CANDIDATE_DUPE_CLUSTERS,
        {'review_id': review_id})

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


def sanitize_and_validate_citation_status(record):
    sanitized_status = cipy.validation.citation_status.sanitize(record)
    citation_status = cipy.validation.citation_status.CitationStatus(sanitized_status)
    try:
        citation_status.validate()
    except ModelValidationError:
        msg = 'invalid record: {}'.format(sanitized_status)
        LOGGER.exception(msg)
    return citation_status.to_primitive()


def main():
    parser = argparse.ArgumentParser(
        description='De-duplicate citation records!')
    parser.add_argument(
        '--review_id', type=int, required=True, metavar='review_id',
        help='unique identifier of current systematic map review')
    parser.add_argument(
        '--settings', type=str, required=True, metavar='settings_file_path',
        help='path to file on disk where dedupe model settings are saved')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL',
        help='environment variable to which Postgres connection credentials have been assigned')
    parser.add_argument(
        '--threshold', type=str, metavar='dedupe_score_threshold', default='auto',
        help="""float value in [0.0, 1.0] above which duplicates are automatically
        assigned; if 'auto' (default), an ideal value will be computed from data""")
    parser.add_argument(
        '--test', action='store_true', default=False,
        help='flag to run script without modifying any data or models')
    args = parser.parse_args()

    act = not args.test

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    citations_db = cipy.db.PostgresDB(conn_creds, ddl='citations')
    status_db = cipy.db.PostgresDB(conn_creds, ddl='citation_status')
    status_db.create_table(act=act)
    status_db.create_indexes(act=act)

    # create dedupe blocking tables and indexes if they don't yet exist
    citations_db.execute(CREATE_DEDUPE_BLOCKING_MAP, act=act)
    citations_db.execute(
        """
        CREATE INDEX IF NOT EXISTS dedupe_blocking_map_key_idx
        ON dedupe_blocking_map (block_key)
        """, act=act)

    # remove rows for this particular review
    # which we'll then add back with the latest citations included
    citations_db.execute(
        DELETE_REVIEW_ROWS.format(table='dedupe_blocking_map'),
        bindings={'review_id': args.review_id}, act=act)

    if os.path.exists(args.settings):
        LOGGER.info('reading dedupe settings from %s', args.settings)
        deduper = cipy.db.get_deduper(args.settings, num_cores=2)

    # if dedupe learned an Index Predicate
    # we have to take a pass through the data and create indices
    LOGGER.info('creating dedupe_blocking_map table...')

    column_types = {column.get('column_name') or column['name']: column['data_type']
                    for column in citations_db.ddl['schema']['columns']}
    for field in deduper.blocker.index_fields:
        query = """
            SELECT DISTINCT {col}
            FROM {table}
            WHERE review_id = %(review_id)s
            """.format(col=field, table=citations_db.ddl.get_name('table'))
        results = citations_db.run_query(
            query, {'review_id': args.review_id})
        field_type = column_types[field]
        if 'array' in field_type.lower():
            field_data = (tuple(row[field]) for row in results
                          if row and row.get(field))
        else:
            field_data = (row[field] for row in results if row)
        deduper.blocker.index(field_data, field)

    # now we're ready to write our blocking map table by creating a generator
    # that yields unique (block_key, citation_id, review_id) tuples
    data = ((row['citation_id'], cipy.db.make_immutable(row))
            for row in citations_db.run_query(
                citations_db.ddl['templates']['select_citations_basic_info']))
    b_data = ((block_key, citation_id, args.review_id)
              for block_key, citation_id in deduper.blocker(data))

    # write out blocking map to CSV so we can quickly load in with Postgres COPY
    csv_file = tempfile.NamedTemporaryFile(prefix='blocks_',
                                           delete=False,
                                           mode='wt')
    csv_writer = csv.writer(csv_file)
    csv_writer.writerows(b_data)
    csv_file.close()

    if act is True:
        try:
            with io.open(csv_file.name, mode='rt') as f:
                with citations_db.conn.cursor() as cur:
                    cur.copy_expert('COPY dedupe_blocking_map FROM STDIN CSV', f)
        except psycopg2.DataError:
            LOGGER.exception()
    else:
        LOGGER.info(
            'query: "COPY dedupe_blocking_map FROM STDIN CSV %s"', csv_file.name)

    os.remove(csv_file.name)

    # many block keys will form blocks that only contain a single record
    # since there are no comparisons possible withing such a singleton block
    # we can ignore them
    LOGGER.info("creating dedupe_plural_key and dedupe_plural_block tables...")

    # create tables and indexes if they don't already exist
    citations_db.execute(CREATE_DEDUPE_PLURAL_KEY, act=act)
    citations_db.execute(CREATE_DEDUPE_PLURAL_BLOCK, act=act)

    # TODO: can this index be unique in the case of multiple reviews?!?
    citations_db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dedupe_block_key_idx
        ON dedupe_plural_key (block_key)
        """, act=act)
    citations_db.execute(
        """
        CREATE INDEX IF NOT EXISTS dedupe_plural_block_citation_id_idx
        ON dedupe_plural_block (citation_id)
        """, act=act)
    citations_db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dedupe_plural_block_block_id_citation_id_uniq
        ON dedupe_plural_block (block_id, citation_id)
        """, act=act)

    # now remove rows for this particular review
    citations_db.execute(
        DELETE_REVIEW_ROWS.format(table='dedupe_plural_key'),
        bindings={'review_id': args.review_id}, act=act)
    citations_db.execute(
        DELETE_REVIEW_ROWS.format(table='dedupe_plural_block'),
        bindings={'review_id': args.review_id}, act=act)

    # now add all this review's rows (back) in
    citations_db.execute(
        """
        INSERT INTO dedupe_plural_key (block_key, review_id)
        SELECT block_key, MIN(review_id)
        FROM dedupe_blocking_map
        GROUP BY block_key
        HAVING COUNT(1) > 1 AND MIN(review_id) = %(review_id)s
        """, bindings={'review_id': args.review_id}, act=act)
    citations_db.execute(
        """
        INSERT INTO dedupe_plural_block (block_id, citation_id, review_id)
        SELECT t1.block_id, t2.citation_id, t2.review_id
        FROM
            dedupe_plural_key AS t1,
            dedupe_blocking_map AS t2
        WHERE
            t1.block_key = t2.block_key
            AND t2.review_id = %(review_id)s
        """, bindings={'review_id': args.review_id}, act=act)

    # To use Kolb, et. al's Redundant Free Comparison scheme, we need to
    # keep track of all the block_ids that are associated with particular
    # citation records
    LOGGER.info('creating dedupe_covered_blocks table...')

    # create table and index if it doesn't already exist
    citations_db.execute(CREATE_DEDUPE_COVERED_BLOCKS, act=act)
    citations_db.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS dedupe_covered_blocks_citation_id_idx
        ON dedupe_covered_blocks (citation_id)
        """)

    # remove rows for this particular review
    citations_db.execute(
        DELETE_REVIEW_ROWS.format(table='dedupe_covered_blocks'),
        bindings={'review_id': args.review_id}, act=act)

    # then add the rows back in
    citations_db.execute(
        """
        INSERT INTO dedupe_covered_blocks (citation_id, review_id, sorted_ids)
        SELECT
            citation_id, MIN(review_id),
            string_agg(CAST(block_id AS TEXT), ',' ORDER BY block_id)
        FROM dedupe_plural_block
        GROUP BY citation_id
        HAVING MIN(review_id) = %(review_id)s
        """, bindings={'review_id': args.review_id}, act=act)

    # for every block of records, we need to keep track of a citation records's
    # associated block_ids that are SMALLER than the current block's id
    LOGGER.info("creating dedupe_smaller_coverage table...")

    # create table if it doesn't already exist, and remove rows for this review
    citations_db.execute(CREATE_DEDUPE_SMALLER_COVERAGE, act=act)
    citations_db.execute(
        DELETE_REVIEW_ROWS.format(table='dedupe_smaller_coverage'),
        bindings={'review_id': args.review_id}, act=act)

    # now add in the rows
    citations_db.execute(
        """
        INSERT INTO dedupe_smaller_coverage (citation_id, review_id, block_id, smaller_ids)
        SELECT
            t1.citation_id, t1.review_id, t1.block_id,
            TRIM(',' FROM split_part(t2.sorted_ids, CAST(t1.block_id AS TEXT), 1))
        FROM
            dedupe_plural_block AS t1,
            dedupe_covered_blocks AS t2
        WHERE
            t1.citation_id = t2.citation_id
            AND t1.review_id = %(review_id)s
        """, bindings={'review_id': args.review_id}, act=act)

    # okay, now let's load up our dedupe model and set its threshold
    LOGGER.info('reading dedupe settings from %s', args.settings)
    deduper = cipy.db.get_deduper(args.settings, num_cores=4)

    if args.threshold == 'auto':
        results = citations_db.run_query(
            citations_db.ddl['templates']['select_sample_for_dupe_threshold'],
            {'review_id': args.review_id})
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

    # apply model to get clusters of duplicate records
    clustered_dupes = deduper.matchBlocks(
        get_candidate_dupes(citations_db, args.review_id),
        threshold=dupe_threshold)
    LOGGER.info('found %s duplicate clusters', len(clustered_dupes))

    duplicate_cids = set()
    for cids, scores in clustered_dupes:
        citation_duplicate_scores = {cid: score
                                     for cid, score in zip(cids, scores)}
        canonical_citation = citations_db.run_query(
            citations_db.ddl['templates']['select_dupe_cluster_canonical_id'],
            {'review_id': args.review_id,
             'citation_ids': tuple(int(cid) for cid in cids)})
        canonical_citation_id = tuple(canonical_citation)[0]['citation_id']

        for cid, score in citation_duplicate_scores.items():
            if cid == canonical_citation_id:
                continue
            duplicate_cids.add(cid)
            citation_status = {
                'citation_id': cid,
                'review_id': args.review_id,
                'status': 'excluded',
                'exclude_reason': 'deduplication',
                'deduplication': {'is_duplicate': True,
                                  'is_duplicate_of': canonical_citation_id,
                                  'duplicate_score': score}
                }
            validated_cs = sanitize_and_validate_citation_status(citation_status)
            validated_cs = cipy.db.db_utils.dump_json_fields_to_str(
                validated_cs, {'deduplication'})
            status_db.execute(
                status_db.ddl['templates']['upsert_duplicates'],
                validated_cs, act=act)

    LOGGER.info('upserted status for %s duplicate citations %s',
                len(duplicate_cids), '' if act is True else '(TEST)')

    review_citations = citations_db.run_query(
        'SELECT citation_id FROM citations WHERE review_id = %(review_id)s',
        {'review_id': args.review_id})
    all_cids = {record['citation_id'] for record in review_citations}
    nonduplicate_cids = sorted(all_cids - duplicate_cids)
    for cid in nonduplicate_cids:
        citation_status = {
            'citation_id': cid,
            'review_id': args.review_id,
            'status': 'included',
            'exclude_reason': None,
            'deduplication': {'is_duplicate': False}
            }
        validated_cs = sanitize_and_validate_citation_status(citation_status)
        validated_cs = cipy.db.db_utils.dump_json_fields_to_str(
            validated_cs, {'deduplication'})
        status_db.execute(
            status_db.ddl['templates']['upsert_nonduplicates'],
            validated_cs, act=act)

    LOGGER.info('upserted status for %s non-duplicate citations %s',
                len(nonduplicate_cids), '' if act is True else '(TEST)')


if __name__ == '__main__':
    sys.exit(main())
