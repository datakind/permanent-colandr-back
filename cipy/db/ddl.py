from __future__ import absolute_import, division, print_function, unicode_literals

import io

import yaml


CREATE_TABLE_STMT = 'CREATE TABLE IF NOT EXISTS {table_name} ({columns}) {table_constraints}'
CREATE_VIEW_STMT = 'CREATE OR REPLACE {view_name} AS {tables}'
DROP_TABLE_STMT = 'DROP TABLE IF EXISTS {table_name}'
INSERT_VALUES_STMT = 'INSERT INTO {table_name} ({columns}) VALUES {values}'
INSERT_SUBQUERY_STMT = 'INSERT INTO {table_name} ({subquery})'


class DDL(object):
    """
    Args:
        path (str): path to ddl yaml file on disk

    Attributes:
        data (dict): all parsed data loaded from the input ddl yaml file
    """

    def __init__(self, path):
        with io.open(path, mode='rt') as f:
            self.data = yaml.load(f)

    def _get_name(self, which, name_format_inputs):
        full_name = '{}_name'.format(which)
        name = self.data['schema'].get(full_name) or self.data['schema']['name']
        if not name_format_inputs:
            return name
        if isinstance(name_format_inputs, str):
            name = name.format(name_format_inputs)
        elif isinstance(name_format_inputs, (tuple, list)):
            name = name.format(*name_format_inputs)
        elif isinstance(name_format_inputs, dict):
            name = name.format(**name_format_inputs)
        else:
            msg = 'name_format_inputs type "{}" not valid'.format(type(name_format_inputs))
            raise ValueError(msg)
        return name

    def create_table_statement(self, name_format_inputs=None):
        """
        Args:
            name_format_inputs (str, list[str], or dict): values to be passed into
                a `.format()` str for the table name; str for a single value,
                list[str] for an ordered sequence of values, and dict for a mapping
                of field names to values

        Returns:
            str: create table statement, made by filling in template's values
        """
        template = self.data.get('templates', {}).get('create_table', CREATE_TABLE_STMT).strip()
        table_name = self._get_name('table', name_format_inputs)
        columns = [(column.get('column_name') or column['name'],
                    column['data_type'],
                    column.get('constraints', ''))
                   for column in self.data['schema']['columns']]
        columns = ', '.join(' '.join(comp for comp in column if comp)
                            for column in columns)
        table_constraints = self.data['schema'].get('table_constraints', '')
        return template.format(table_name=table_name,
                               columns=columns,
                               table_constraints=table_constraints)

    def create_view_statement(self, tables, name_format_inputs=None):
        """
        Args:
            tables (sequence[str])
            name_format_inputs (str, list[str], or dict): values to be passed into
                a `.format()` str for the table name; str for a single value,
                list[str] for an ordered sequence of values, and dict for a mapping
                of field names to values

        Returns:
            str: create view statement, made by filling in template's values
        """
        template = self.data.get('templates', {}).get('create_view', CREATE_VIEW_STMT).strip()
        view_name = self._get_name('view', name_format_inputs)
        tables = ' UNION ALL '.join(tables)
        return template.format(view_name=view_name, tables=tables)

    def drop_table_statement(self, name_format_inputs=None):
        """
        Args:
            name_format_inputs (str, list[str], or dict): values to be passed into
                a `.format()` str for the table name; str for a single value,
                list[str] for an ordered sequence of values, and dict for a mapping
                of field names to values

        Returns:
            str: drop table statement, made by filling in template's values
        """
        template = self.data.get('templates', {}).get('drop_table', DROP_TABLE_STMT).strip()
        table_name = self._get_name('table', name_format_inputs)
        return template.format(table_name=table_name)

    def insert_values_statement(self, named_args=True, columns=None,
                                name_format_inputs=None):
        """
        Args:
            named_args (bool): if True, values to be inserted must be dicts;
                if False, values must be tuples
            columns (sequence[str]): column names of rows to be inserted;
                NB: if `named_args` is True, column order matters; otherwise, not
            name_format_inputs (str, list[str], or dict): values to be passed into
                a `.format()` str for the table name; str for a single value,
                list[str] for an ordered sequence of values, and dict for a mapping
                of field names to values

        Returns:
            str: insert values statement, made by filling in template's values
        """
        template = self.data.get('templates', {}).get('insert_values', INSERT_VALUES_STMT).strip()
        table_name = self._get_name('table', name_format_inputs)
        if columns is None:
            columns = [column.get('column_name') or column['name']
                       for column in self.data['schema']['columns']]
        if named_args is True:
            values = '(' + ', '.join('%(' + column + ')s' for column in columns) + ')'
        else:
            values = '(' + ', '.join('%s' for column in columns) + ')'
        columns = ', '.join(columns)
        return template.format(table_name=table_name,
                               columns=columns,
                               values=values)

    def insert_subquery_statement(self, subquery, name_format_inputs=None):
        """
        Args:
            subquery (str): valid SQL query that returns rows to be inserted
            name_format_inputs (str, list[str], or dict): values to be passed into
                a `.format()` str for the table name; str for a single value,
                list[str] for an ordered sequence of values, and dict for a mapping
                of field names to values

        Returns:
            str: insert subquery statement, made by filling in template's values
        """
        template = self.data.get('templates', {}).get('insert_subquery', INSERT_SUBQUERY_STMT).strip()
        table_name = self._get_name('table', name_format_inputs)
        return template.format(table_name=table_name, subquery=subquery)
