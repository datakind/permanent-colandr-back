#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import json
import logging

from schematics.exceptions import ModelValidationError

import cipy

logger = logging.getLogger('ingest_citations')
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="""Load, parse, normalize, transform, sanitize, and validate
                    a collection of citation records, then insert them into a db.""")
    parser.add_argument(
        'ddl', type=str, metavar='psql_ddl_file_path')
    parser.add_argument(
        'citations', type=str, metavar='citations_file_path')
    parser.add_argument(
        '--dbname', type=str, metavar='psql_database_name', default='appname')
    parser.add_argument(
        '--username', type=str, metavar='psql_user_name', default='app')
    parser.add_argument(
        '--host', type=str, metavar='psql_host', default='localhost')
    parser.add_argument(
        '--port', type=int, metavar='psql_port', default=5432)
    parser.add_argument(
        '--dry-run', action='store_true', default=False)
    args = parser.parse_args()

    conn_creds = {'dbname': args.dbname, 'user': args.username,
                  'host': args.host, 'port': args.port}
    psql = cipy.db.PostgresDB(args.ddl, conn_creds)
    if args.dry_run is False:
        psql.create_table()

    if args.citations.endswith('.bib'):
        citations_file = cipy.parsers.BibTexFile(args.citations)
    elif args.citations.endswith('.ris') or args.citations.endswith('.txt'):
        citations_file = cipy.parsers.RisFile(args.citations)

    n_valid_records = 0
    n_invalid_records = 0
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
            logger.exception(msg)
            n_invalid_records += 1
            continue

        n_valid_records += 1

        validated_record = c.to_primitive()
        validated_record['other_fields'] = json.dumps(validated_record['other_fields'])

        if args.dry_run is True:
            msg = 'valid record: {}, {}'.format(
                validated_record.get('title'), validated_record.get('publication_year'))
            logger.info(msg)
        else:
            psql.insert_values(validated_record)

    msg = '{} valid records inserted into {} db'.format(n_valid_records, args.dbname)
    logger.info(msg)
    if n_invalid_records > 0:
        msg = '{} invalid records skipped'.format(n_invalid_records)
        logger.warning(msg)
