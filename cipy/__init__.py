import logging

# subpackages
from cipy import db
from cipy import parsers
# top-level modules
from cipy import hack

logger = logging.getLogger('cipy')
if len(logger.handlers) == 0:  # to ensure reload() doesn't add another one
    logger.addHandler(logging.NullHandler())
