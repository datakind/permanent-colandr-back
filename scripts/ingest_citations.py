#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import logging
import os
import sys

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('ingest_citations')
LOGGER.setLevel(logging.INFO)
if len(LOGGER.handlers) == 0:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    _handler.setFormatter(_formatter)
    LOGGER.addHandler(_handler)


def main():
    parser = argparse.ArgumentParser(
        description="""Load, parse, normalize, transform, sanitize, and validate
                    a collection of citation records, then insert them into a db.""")
    parser.add_argument(
        '--citations', type=str, required=True, nargs='+', metavar='citations_file_path',
        help="""path to 1 or multiple files on disk containing citation records in
             BibTex or RIS format""")
    parser.add_argument(
        '--user_id', type=int, required=True, metavar='user_id',
        help='unique identifier of current user')
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
    citations_db = cipy.db.PostgresDB(conn_creds, ddl='citations')
    citations_db.create_table(act=act)

    n_valid_total = 0
    n_invalid_total = 0
    for citations_file_path in sorted(set(args.citations)):

        if not os.path.exists(citations_file_path):
            msg = 'citations file "{}" does not exist'.format(citations_file_path)
            raise OSError(msg)

        LOGGER.info('parsing records in %s', citations_file_path)
        if citations_file_path.endswith('.bib'):
            citations_file = cipy.parsers.BibTexFile(citations_file_path)
        elif citations_file_path.endswith('.ris') or citations_file_path.endswith('.txt'):
            citations_file = cipy.parsers.RisFile(citations_file_path)

        n_valid = 0
        n_invalid = 0
        for record in citations_file.parse():

            record['review_id'] = args.review_id
            record['user_id'] = args.user_id
            sanitized_record = cipy.validation.citation.sanitize(record)

            c = cipy.validation.citation.Citation(sanitized_record)
            try:
                c.validate()
            except ModelValidationError:
                msg = 'invalid record: {}, {}'.format(
                    sanitized_record.get('title'), sanitized_record.get('publication_year'))
                LOGGER.exception(msg)
                n_invalid += 1
                continue

            n_valid += 1

            validated_record = c.to_primitive()
            validated_record['other_fields'] = json.dumps(validated_record['other_fields'])

            if act is True:
                citations_db.insert_values(validated_record, act=act)
            else:
                msg = 'valid record: {}, {}'.format(
                    validated_record.get('title'), validated_record.get('publication_year'))
                LOGGER.info(msg)

        msg = '{} valid records inserted into {} db {}'.format(
            n_valid, conn_creds['dbname'], '(TEST)' if args.test else '')
        LOGGER.info(msg)
        if n_invalid > 0:
            msg = '{} invalid records skipped'.format(n_invalid)
            LOGGER.warning(msg)

        n_valid_total += n_valid
        n_invalid_total += n_invalid

    if len(args.citations) > 1:
        msg = '{} total valid records inserted into {} db {}'.format(
            n_valid_total, conn_creds['dbname'], '(TEST)' if args.test else '')
        LOGGER.info(msg)
        if n_invalid_total > 0:
            msg = '{} total invalid records skipped'.format(n_invalid_total)
            LOGGER.warning(msg)


if __name__ == '__main__':
    sys.exit(main())
