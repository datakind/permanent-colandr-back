from __future__ import absolute_import, division, print_function, unicode_literals

from datetime import datetime

import arrow
from schematics.models import Model
from schematics.types import DictType, IntType, ListType, StringType, UTCDateTimeType

from cipy.validation.sanitizers import sanitize_integer, sanitize_string, sanitize_type


FIELD_SANITIZERS = {
    'created_ts': lambda x: sanitize_type(x, datetime),
    'project_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'user_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'type_of_work': lambda x: sanitize_string(x, max_length=25),
    'title': lambda x: sanitize_string(x, max_length=250),
    'secondary_title': lambda x: sanitize_string(x, max_length=250),
    'publication_year': lambda x: sanitize_integer(x, max_value=32767),
    'publication_month': lambda x: sanitize_integer(x, max_value=32767),
    'authors': lambda x: [sanitize_string(item, max_length=100) for item in x],
    'abstract': sanitize_string,
    'keywords': lambda x: [sanitize_string(item, max_length=100) for item in x],
    'type_of_reference': lambda x: sanitize_string(x, max_length=50),
    'journal_name': lambda x: sanitize_string(x, max_length=100),
    'volume': lambda x: sanitize_string(x, max_length=20),
    'issue_number': lambda x: sanitize_string(x, max_length=20),
    'doi': lambda x: sanitize_string(x, max_length=100),
    'issn': lambda x: sanitize_string(x, max_length=20),
    'publisher': lambda x: sanitize_string(x, max_length=100),
    'language': lambda x: sanitize_string(x, max_length=50)
}


def sanitize(record):
    """
    After parsing but before creating a `Citation` model, sanitize the values
    in a citation `record` so that they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    sanitized_record = {'other_fields': {}}
    for key, value in record.items():
        try:
            sanitized_record[key] = FIELD_SANITIZERS[key](value)
        except KeyError:
            sanitized_record['other_fields'][key] = sanitize_type(value, str)
    return sanitized_record


class Citation(Model):
    project_id = IntType(required=True,
                         min_value=0, max_value=2147483647)
    user_id = IntType(required=True,
                      min_value=0, max_value=2147483647)
    created_ts = UTCDateTimeType(default=arrow.utcnow().datetime,
                                 convert_tz=True, drop_tzinfo=True)
    type_of_work = StringType(max_length=25)
    title = StringType(max_length=250)
    secondary_title = StringType(max_length=250)
    publication_year = IntType(min_value=0, max_value=32767)
    publication_month = IntType(min_value=0, max_value=32767)
    authors = ListType(StringType(max_length=100))
    abstract = StringType()
    keywords = ListType(StringType(max_length=100))
    type_of_reference = StringType(max_length=50)
    journal_name = StringType(max_length=100)
    volume = StringType(max_length=20)
    issue_number = StringType(max_length=20)
    doi = StringType(max_length=100)
    issn = StringType(max_length=20)
    publisher = StringType(max_length=100)
    language = StringType(max_length=50)
    other_fields = DictType(StringType)
