import logging
import os

DEFAULT_DDL_PATHS = {}
_ddls_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ddls')
for fname in os.listdir(_ddls_path):
    if fname.endswith('yaml'):
        path = os.path.join(_ddls_path, fname)
        key, _ = os.path.splitext(fname)
        DEFAULT_DDL_PATHS[key] = path

# subpackages
from cipy import db
from cipy import parsers
from cipy import validation
# top-level modules
from cipy import utils
from cipy import hacks

logger = logging.getLogger('cipy')
if len(logger.handlers) == 0:  # to ensure reload() doesn't add another one
    logger.addHandler(logging.NullHandler())
