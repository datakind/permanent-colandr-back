from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

import arrow
from schematics.models import Model
from schematics.types import IntType, ListType, ModelType, StringType, UTCDateTimeType

from cipy.validation.sanitizers import sanitize_integer, sanitize_string, sanitize_type


FIELD_SANITIZERS = {
    'created_ts': lambda x: sanitize_type(x, datetime),
    'owner_user_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'user_ids': lambda x: [sanitize_integer(item, min_value=0, max_value=2147483647)
                           for item in x],
    'name': lambda x: sanitize_string(x, max_length=500),
    'description': sanitize_string,
    'num_citation_screening_reviewers': lambda x: sanitize_integer(x, min_value=1, max_value=3),
    'num_fulltext_screening_reviewers': lambda x: sanitize_integer(x, min_value=1, max_value=3),
    'required_citation_screener_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'required_fulltext_screener_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    }


def sanitize(record):
    """
    After parsing but before creating a `Review` model, sanitize the values
    in a review `record` so that they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    sanitized_record = {}
    for key, value in record.items():
        if key == 'settings' and value:
            sanitized_record[key] = {subkey: FIELD_SANITIZERS[subkey](subvalue)
                                     for subkey, subvalue in value.items()}
        elif value:
            sanitized_record[key] = FIELD_SANITIZERS[key](value)
    return sanitized_record


class Settings(Model):
    num_citation_screening_reviewers = IntType(
        required=True, min_value=1, max_value=3, default=2)
    num_fulltext_screening_reviewers = IntType(
        required=True, min_value=1, max_value=3, default=2)
    required_citation_screener_id = IntType(min_value=0, max_value=2147483647)
    required_fulltext_screener_id = IntType(min_value=0, max_value=2147483647)


class Review(Model):
    created_ts = UTCDateTimeType(default=arrow.utcnow().datetime,
                                 convert_tz=True, drop_tzinfo=True)
    owner_user_id = IntType(required=True,
                            min_value=0, max_value=2147483647)
    user_ids = ListType(IntType(min_value=0, max_value=2147483647),
                        required=True)
    name = StringType(required=True,
                      max_length=500)
    description = StringType()
    settings = ModelType(Settings, default=Settings())
