from __future__ import absolute_import, division, print_function, unicode_literals

import io

import psycopg2
import yaml

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

    def run_query(self, query, bindings=None, act=True):
        with self.conn.cursor() as cur:
            print(cur.mogrify(query, bindings))
            if act is True:
                cur.execute(query, bindings)
