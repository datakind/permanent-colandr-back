from __future__ import absolute_import, division, print_function, unicode_literals

from schematics.models import Model
from schematics.types import (BooleanType, FloatType, IntType, ListType,
                              ModelType, StringType)

from cipy.validation.sanitizers import (sanitize_float, sanitize_integer,
                                        sanitize_string, sanitize_type)


FIELD_SANITIZERS = {
    'citation_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'review_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'confirmed_by': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'screened_by': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'status': lambda x: sanitize_string(x, max_length=8),
    'is_duplicate': lambda x: sanitize_type(x, bool),
    'is_duplicate_of': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'duplicate_score': lambda x: sanitize_float(x, min_value=0.0, max_value=1.0),
    'labels': lambda x: [sanitize_string(item, max_length=25) for item in x]
    }


def sanitize(record):
    """
    After parsing but before creating a `CitationStatus` model, sanitize the values
    in `record` so they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    model_keys = {'deduplication', 'screening_1', 'screening_2', 'screening_3'}
    sanitized_record = {}
    for key, value in record.items():
        if key in model_keys and value:
            sanitized_record[key] = {subkey: FIELD_SANITIZERS[subkey](subvalue)
                                     for subkey, subvalue in value.items()}
        elif value:
            sanitized_record[key] = FIELD_SANITIZERS[key](value)
    return sanitized_record


class Deduplication(Model):
    is_duplicate = BooleanType(required=True)
    is_duplicate_of = IntType(min_value=0, max_value=2147483647)
    duplicate_score = FloatType(min_value=0.0, max_value=1.0)
    confirmed_by = IntType(min_value=0, max_value=2147483647)


class Screening(Model):
    status = StringType(required=True, max_length=8)
    labels = ListType(StringType(max_length=25))
    screened_by = IntType(required=True, min_value=0, max_value=2147483647)


class CitationStatus(Model):
    citation_id = IntType(
        required=True, min_value=0, max_value=2147483647)
    review_id = IntType(
        required=True, min_value=0, max_value=2147483647)
    status = StringType(required=True, max_length=8)
    deduplication = ModelType(Deduplication)
    screening_1 = ModelType(Screening)
    screening_2 = ModelType(Screening)
    screening_3 = ModelType(Screening)
