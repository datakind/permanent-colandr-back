from __future__ import absolute_import, division, print_function, unicode_literals

from schematics.models import Model
from schematics.types import (ModelType, DictType, IntType, ListType, StringType,
                              URLType, UTCDateTimeType)

from cipy.validation.sanitizers import sanitize_integer, sanitize_string, sanitize_type

# TODO!
FIELD_SANITIZERS = {}


def sanitize(record):
    """
    After parsing but before creating a `ReviewPlan` model, sanitize the values
    in a review plan `record` so that they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    return {key: FIELD_SANITIZERS[key](value)
            for key, value in record.items()}


class ResearchQuestion(Model):
    text = StringType(required=True)
    rank = IntType(required=True)


class Keyterm(Model):
    text = StringType(required=True)
    synonyms = ListType(StringType)
    group = StringType(required=True)


class DataSource(Model):
    name = StringType(required=True)
    url = URLType(required=True)
    notes = StringType()


class SelectionCriterion(Model):
    label = StringType(required=True)
    explanation = StringType()


class ReviewPlan(Model):
    review_id = IntType(required=True,
                        min_value=0, max_value=2147483647)
    objective = StringType()
    research_questions = ListType(ModelType(ResearchQuestion))
    pico = DictType()
    keyterms = ListType(ModelType(Keyterm))
    data_sources = ListType(ModelType(DataSource))
    inclusion_criteria = ListType(ModelType(SelectionCriterion))
    exclusion_criteria = ListType(ModelType(SelectionCriterion))
