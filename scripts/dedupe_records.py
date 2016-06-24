#!/usr/bin/env python
from __future__ import absolute_import, division, print_function, unicode_literals

import argparse
import io
import logging
import os

import dedupe

import cipy

LOGGER = logging.getLogger('dedupe_records')
LOGGER.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
_handler.setFormatter(_formatter)
LOGGER.addHandler(_handler)


if __name__ == '__main__':

    parser = argparse.ArgumentParser(
        description="""Deduplicate citation records.""")
    parser.add_argument(
        '--project_id', type=int, required=True, metavar='project_id')
    parser.add_argument(
        '--ddls', type=str, metavar='psql_ddls_dir', default=cipy.db.DEFAULT_DDLS_PATH)
    parser.add_argument(
        '--settings', type=str, required=True, metavar='settings_file_path')
    parser.add_argument(
        '--database_url', type=str, metavar='psql_database_url', default='DATABASE_URL')
    parser.add_argument(
        '--threshold', type=str, metavar='dedupe_score_threshold', default='auto')
    parser.add_argument(
        '--dryrun', action='store_true', default=False)
    args = parser.parse_args()

    conn_creds = cipy.db.get_conn_creds(args.database_url)

    citations_ddl = cipy.db.get_ddl('citations', ddls_path=args.ddls)
    citations_db = cipy.db.PostgresDB(conn_creds, citations_ddl)
    duplicates_ddl = cipy.db.get_ddl('duplicates', ddls_path=args.ddls)
    duplicates_db = cipy.db.PostgresDB(conn_creds, duplicates_ddl)

    LOGGER.info('reading dedupe settings from %s', args.settings)
    deduper = cipy.db.get_deduper(args.settings, num_cores=2)

    duplicates_db.create_table()
