from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import io
import itertools
import re

import psycopg2
from psycopg2.extras import RealDictCursor
import yaml

LOGGER = logging.getLogger(__name__)

CREATE_TABLE_STMT = "CREATE TABLE IF NOT EXISTS {table_name} ({columns})"
DROP_TABLE_STMT = "DROP TABLE IF EXISTS {table_name}"
INSERT_VALUES_STMT = "INSERT INTO {table_name}({columns}) VALUES ({values})"


class PostgresDB(object):

    def __init__(self, ddl_path, conn_creds):
        with io.open(ddl_path, mode='rt') as f:
            self.ddl = yaml.load(f)
        self.conn = psycopg2.connect(**conn_creds)
        self.conn.autocommit = True

    def create_table(self):
        stmt = CREATE_TABLE_STMT.format(
            table_name=self.ddl['table_name'],
            columns=', '.join(column['name'] + ' ' + column['type']
                              for column in self.ddl['columns'])
        )
        self.run_query(stmt)

    def drop_table(self):
        stmt = DROP_TABLE_STMT.format(table_name=self.ddl['table_name'])
        self.run_query(stmt)

    def insert_values(self, record):
        columns = list(record.keys())
        values = ', '.join('%({})s'.format(column) for column in columns)
        stmt = INSERT_VALUES_STMT.format(
            table_name=self.ddl['table_name'],
            columns=', '.join(columns),
            values=values
        )
        self.run_query(stmt, bindings=record)

    def run_query(self, query, bindings=None, act=True,
                  cursor_factory=RealDictCursor, itersize=5000):
        with self.conn as conn:

            # first check validity of query
            with conn.cursor() as cur:
                try:
                    mogrified_query = cur.mogrify(query, bindings)
                except Exception as e:
                    LOGGER.exception('malformed query: %s', query)
                    raise e

            with conn.cursor(cursor_factory=cursor_factory) as cur:
                cur.itersize = itersize
                if act is True:
                    cur.execute(mogrified_query)
                    for result in cur:
                        yield result
                else:
                    print(mogrified_query)

    def get_tables(self, table_schema='public',
                   table_type='BASE TABLE',
                   re_match=None,
                   include_views=True):
        """
        Get a list of tables (includes views, by default).
        Args:
            table_schema (str, optional): schema name the table belongs to
            table_type (str, optional): type of the table
            re_match (str, optional): if not None, must be a valid regex pattern
                against which tables will be matched; only matching tables
                are returned
            include_views (bool, optional): if True, also check for matching views

        Returns:
            list(str): sorted list of table names
        """
        if include_views is True:
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE
                table_schema=%(table_schema)s
                AND (table_type=%(table_type)s OR table_type='VIEW')
            ORDER BY table_name ASC
            """
        else:
            query = """
            SELECT table_name
            FROM information_schema.tables
            WHERE
                table_schema=%(table_schema)s
                AND table_type=%(table_type)s
            ORDER BY table_name ASC
            """

        bindings = {
            'table_schema': table_schema,
            'table_type': table_type,
        }
        tables = list(itertools.chain.from_iterable(
            self.run_query(query, bindings=bindings, cursor_factory=None)))
        if re_match is not None:
            re_match = re.compile(re_match)
            tables = [table for table in tables
                      if re_match.search(table)]
        return tables

    def print_table_spec(self, table_name):
        """
        Print information about a table's structure in a nicely formatted table.

        Args:
            table_name (str): name of the table to inspect
        """
        query = """
        SELECT
            column_name, ordinal_position, data_type,
            is_nullable, character_maximum_length
        FROM information_schema.columns
        WHERE table_name=%(table_name)s
        ORDER BY ordinal_position ASC
        """
        results = self.run_query(query, bindings={'table_name': table_name},
                                 cursor_factory=None)
        columns = ('name', 'pos', 'type', 'nullable', 'max_length')
        print('{0:<20} {1:>3} {2:<30} {3:<8} {4:<10}'.format(*columns))
        print('-' * 75)
        for result in results:
            try:
                print('{0:<20} {1:>3} {2:<30} {3:<8} {4:<10}'.format(*result))
            except TypeError:
                print('{0:<20} {1:>3} {2:<30} {3:<8} {4:<10}'.format(
                    *(value if value else '' for value in result)))
