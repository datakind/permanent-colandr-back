from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

import arrow
from schematics.models import Model
from schematics.types import IntType, ListType, StringType, UTCDateTimeType

from cipy.validation.sanitizers import sanitize_integer, sanitize_string, sanitize_type


FIELD_SANITIZERS = {
    'created_ts': lambda x: sanitize_type(x, datetime),
    'creator_user_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'user_ids': lambda x: [sanitize_integer(item, min_value=0, max_value=2147483647)
                           for item in x],
    'name': lambda x: sanitize_string(x, max_length=500),
    'description': sanitize_string
}


def sanitize(record):
    """
    After parsing but before creating a `Project` model, sanitize the values
    in a project `record` so that they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    return {key: FIELD_SANITIZERS[key](value)
            for key, value in record.items()}


class Project(Model):
    created_ts = UTCDateTimeType(default=arrow.utcnow().datetime,
                                 convert_tz=True, drop_tzinfo=True)
    creator_user_id = IntType(required=True,
                              min_value=0, max_value=2147483647)
    user_ids = ListType(IntType(min_value=0, max_value=2147483647),
                        required=True)
    name = StringType(required=True,
                      max_length=500)
    description = StringType()
