import logging
import os

try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse

from cipy.db import DEFAULT_DDLS, DEFAULT_DDLS_PATH

# register database schemes in URLs
urlparse.uses_netloc.append('postgres')
urlparse.uses_netloc.append('postgresql')
urlparse.uses_netloc.append('pgsql')

LOGGER = logging.getLogger(__name__)
DEFAULT_ENV = 'DATABASE_URL'


def get_conn_creds(env_var=DEFAULT_ENV):
    """
    Get Postgres DB connection credentials from a specially-formatted environment
    variable, returned as a dict in the form needed for `psycopg2` to connect.

    Based heavily on https://github.com/kennethreitz/dj-database-url (Copyright 2014,
    Kenneth Reitz. All rights reserved.) but stripped down to just Postgres and
    just connection credentials.

    Args:
        env_var (str): name of environment variable containing connection credentials;
            'DATABASE_URL' is the default value

    Returns:
        dict: connection credentials for Postgres DB, with keys 'dbname', 'user',
            'password', 'host', and 'port'
    """
    db_url = os.environ.get(env_var, None)
    if not db_url:
        msg = 'environment variable "{}" not found'.format(env_var)
        LOGGER.error(msg)
        raise OSError(msg)
    url = urlparse.urlparse(db_url)

    path = url.path[1:]
    if '?' in path and not url.query:
        path, query = path.split('?', 2)
    else:
        path, query = path, url.query
    query = urlparse.parse_qs(query)

    # handle postgres percent-encoded paths
    hostname = url.hostname or ''
    if '%2f' in hostname.lower():
        hostname = hostname.replace('%2f', '/').replace('%2F', '/')

    return {'dbname': urlparse.unquote(path or ''),
            'user': urlparse.unquote(url.username or ''),
            'password': urlparse.unquote(url.password or ''),
            'host': hostname,
            'port': url.port or ''}


def get_ddl(table_name, ddls_path=DEFAULT_DDLS_PATH):
    """
    Get the contents of the `table_name` table's DDL yaml file.

    Args:
        table_name (str): name of table
        ddls_path (str, optional): path on disk where DDL files are saved; by
            default, this is '.../path/to/cipy/db/ddls'

    Returns:
        dict
    """
    if ddls_path == DEFAULT_DDLS_PATH:
        ddls = DEFAULT_DDLS
    else:
        raise NotImplementedError('TODO: fix this!')
    return ddls[table_name]
