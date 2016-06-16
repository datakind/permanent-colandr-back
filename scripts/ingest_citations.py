#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import logging
import os

from schematics.exceptions import ModelValidationError

import cipy

LOGGER = logging.getLogger('ingest_citations')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="""Load, parse, normalize, transform, sanitize, and validate
                    a collection of citation records, then insert them into a db.""")
    parser.add_argument(
        '--ddl', type=str, required=True, metavar='psql_ddl_file_path')
    parser.add_argument(
        '--citations', type=str, required=True, nargs='+', metavar='citations_file_path')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL')
    parser.add_argument(
        '--dryrun', action='store_true', default=False)
    args = parser.parse_args()

    conn_creds = cipy.db.get_conn_creds(args.database_url)
    psql = cipy.db.PostgresDB(args.ddl, conn_creds)
    if args.dryrun is False:
        psql.create_table()

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

            sanitized_record = cipy.db.sanitize_citation(record)
            sanitized_record['project_id'] = cipy.hack.get_project_id()
            sanitized_record['user_id'] = cipy.hack.get_user_id()

            c = cipy.db.Citation(sanitized_record)
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

            if args.dryrun is True:
                msg = 'valid record: {}, {}'.format(
                    validated_record.get('title'), validated_record.get('publication_year'))
                LOGGER.info(msg)
            else:
                psql.insert_values(validated_record)

        msg = '{} valid records inserted into {} db {}'.format(
            n_valid, conn_creds['dbname'], '(DRY RUN)' if args.dryrun else '')
        LOGGER.info(msg)
        if n_invalid > 0:
            msg = '{} invalid records skipped'.format(n_invalid)
            LOGGER.warning(msg)

        n_valid_total += n_valid
        n_invalid_total += n_invalid

    if len(args.citations) > 1:
        msg = '{} total valid records inserted into {} db {}'.format(
            n_valid_total, conn_creds['dbname'], '(DRY RUN)' if args.dryrun else '')
        LOGGER.info(msg)
        if n_invalid_total > 0:
            msg = '{} total invalid records skipped'.format(n_invalid_total)
            LOGGER.warning(msg)
