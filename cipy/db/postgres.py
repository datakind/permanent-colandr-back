from __future__ import absolute_import, division, print_function, unicode_literals

import logging
import itertools
import re

import psycopg2
from psycopg2.extras import RealDictCursor

import cipy

LOGGER = logging.getLogger(__name__)


class PostgresDB(object):

    def __init__(self, conn_creds, ddl=None, autocommit=True):
        if isinstance(ddl, str):
            self.ddl = cipy.db.DDL(ddl)
        elif isinstance(ddl, cipy.db.DDL) or ddl is None:
            self.ddl = ddl
        else:
            msg = 'ddl type "{}" invalid, must be str, ddl.DDL, or None'.format(type(ddl))
            raise ValueError(msg)
        self.conn = psycopg2.connect(**conn_creds)
        self.conn.autocommit = autocommit

    def _check_ddl(self):
        if not self.ddl:
            msg = 'DDL must be specified upon PostgresDB instantiation'
            raise ValueError(msg)

    def execute(self, statement, bindings=None, act=True):
        with self.conn as conn:

            with conn.cursor() as cur:
                try:
                    mogrified_stmt = cur.mogrify(statement, bindings)
                except Exception as e:
                    LOGGER.exception('malformed statement: %s', statement)
                    raise e

            if act is True:
                with conn.cursor() as cur:
                    cur.execute(mogrified_stmt)
            else:
                LOGGER.info('execute: %s', mogrified_stmt)

    def run_query(self, query, bindings=None, act=True,
                  cursor_factory=RealDictCursor, itersize=5000):
        with self.conn as conn:

            with conn.cursor() as cur:
                try:
                    mogrified_query = cur.mogrify(query, bindings)
                except Exception as e:
                    LOGGER.exception('malformed query: %s', query)
                    raise e

            if act is True:
                with conn.cursor(cursor_factory=cursor_factory) as cur:
                    cur.itersize = itersize
                    cur.execute(mogrified_query)
                    for result in cur:
                        yield result
            else:
                LOGGER.info('run_query: %s', mogrified_query)

    def create_table(self, act=True, **template_kwargs):
        self._check_ddl()
        stmt = self.ddl.create_table_statement(**template_kwargs)
        self.execute(stmt, act=act)

    def create_view(self, act=True, **template_kwargs):
        self._check_ddl()
        stmt = self.ddl.create_view_statement(**template_kwargs)
        self.execute(stmt, act=act)

    def drop_table(self, act=True, **template_kwargs):
        self._check_ddl()
        stmt = self.ddl.drop_table_statement(**template_kwargs)
        self.execute(stmt, act=act)

    def insert_values(self, record, named_args=True, columns=None,
                      act=True, **template_kwargs):
        self._check_ddl()
        stmt = self.ddl.insert_values_statement(
            named_args=named_args, columns=columns, **template_kwargs)
        self.execute(stmt, bindings=record, act=act)

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
        print('{0:<30} {1:>3} {2:<30} {3:<8} {4:<10}'.format(*columns))
        print('-' * 85)
        for result in results:
            try:
                print('{0:<30} {1:>3} {2:<30} {3:<8} {4:<10}'.format(*result))
            except TypeError:
                print('{0:<30} {1:>3} {2:<30} {3:<8} {4:<10}'.format(
                    *(value if value else '' for value in result)))
