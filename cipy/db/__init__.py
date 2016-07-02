import io
import os

import yaml

DEFAULT_DDLS_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ddls')
DEFAULT_DDLS = {}
for fname in os.listdir(DEFAULT_DDLS_PATH):
    if fname.endswith('yaml'):
        with io.open(os.path.join(DEFAULT_DDLS_PATH, fname), mode='rt') as f:
            ddl = yaml.load(f)
            key = ddl['schema'].get('table_name') or ddl['schema']['name']
            DEFAULT_DDLS[key] = ddl

from .citation import Citation, sanitize_citation
from . import queries
from .db_utils import get_conn_creds, get_ddl, get_deduper, make_immutable
from .ddl import DDL
from .postgres import PostgresDB
