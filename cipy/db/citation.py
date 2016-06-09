from __future__ import absolute_import, division, print_function, unicode_literals

import arrow
from schematics.models import Model
from schematics.types import (BooleanType, DictType, IntType, ListType, ModelType,
                              StringType, UTCDateTimeType)


class Citation(Model):
    record_id = IntType(required=True,
                        min_value=0, max_value=9223372036854775807)
    project_id = IntType(required=True,
                         min_value=0, max_value=2147483647)
    user_id = IntType(required=True,
                      min_value=0, max_value=2147483647)
    insert_ts = UTCDateTimeType(default=arrow.utcnow().datetime,
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
    is_duplicate = BooleanType(default=None)
