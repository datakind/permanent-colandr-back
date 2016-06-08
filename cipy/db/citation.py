from __future__ import absolute_import, division, print_function, unicode_literals

import arrow
from schematics.models import Model
from schematics import types


# TODO!
class OtherFields(Model):
    empty = True


class Citation(Model):
    record_id = types.IntType(required=True,
                              min_value=0, max_value=9223372036854775807)
    project_id = types.IntType(required=True,
                               min_value=0, max_value=2147483647)
    user_id = types.IntType(required=True,
                            min_value=0, max_value=2147483647)
    insert_ts = types.UTCDateTimeType(required=True, default=arrow.utcnow().datetime,
                                      convert_tz=True, drop_tzinfo=True)
    type_of_work = types.StringType(max_length=25)
    title = types.StringType(max_length=250)
    secondary_title = types.StringType(max_length=250)
    publication_year = types.IntType(min_value=0, max_value=32767)
    publication_month = types.IntType(min_value=0, max_value=32767)
    authors = types.ListType(types.StringType(max_length=100))
    abstract = types.StringType()
    keywords = types.ListType(types.StringType(max_length=100))
    type_of_reference = types.StringType(max_length=50)
    journal_name = types.StringType(max_length=100)
    volume = types.StringType(max_length=20)
    issue_number = types.StringType(max_length=20)
    doi = types.StringType(max_length=100)
    issn = types.StringType(max_length=20)
    publisher = types.StringType(max_length=100)
    language = types.StringType(max_length=50)
    other_fields = types.DictType(types.ModelType(OtherFields))
