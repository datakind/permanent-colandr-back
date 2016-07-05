from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime
import re

import arrow
from schematics.exceptions import ValidationError
from schematics.models import Model
from schematics.types import IntType, ListType, StringType, UTCDateTimeType

from cipy.validation.sanitizers import sanitize_integer, sanitize_string, sanitize_type


EMAIL_REGEX = re.compile(r"(?:^|(?<=[^\w@.)]))([\w+-](\.(?!\.))?)*?[\w+-]@(?:\w-?)*?\w+(\.([a-z]{2,})){1,3}(?:$|(?=\b))", flags=re.IGNORECASE | re.UNICODE)

FIELD_SANITIZERS = {
    'created_ts': lambda x: sanitize_type(x, datetime),
    'name': lambda x: sanitize_string(x, max_length=200),
    'email': lambda x: sanitize_string(x, max_length=200),
    'password': sanitize_string,
    'project_ids': lambda x: [sanitize_integer(item, min_value=0, max_value=2147483647)
                              for item in x],
    'owned_project_ids': lambda x: [sanitize_integer(item, min_value=0, max_value=2147483647)
                                    for item in x],
}


def validate_email(email):
    if EMAIL_REGEX.search(email) is not None:
        return email
    else:
        raise ValidationError('invalid email: "{}"'.format(email))


def sanitize(record):
    """
    After parsing but before creating a `User` model, sanitize the values
    in a user `record` so that they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    return {key: FIELD_SANITIZERS[key](value)
            for key, value in record.items()}


class User(Model):
    created_ts = UTCDateTimeType(default=arrow.utcnow().datetime,
                                 convert_tz=True, drop_tzinfo=True)
    name = StringType(required=True,
                      max_length=200)
    email = StringType(required=True,
                       validators=[validate_email], max_length=200)
    password = StringType(required=True)
    project_ids = ListType(IntType(min_value=0, max_value=2147483647))
    owned_project_ids = ListType(IntType(min_value=0, max_value=2147483647))
