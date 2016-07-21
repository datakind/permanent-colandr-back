from __future__ import absolute_import, division, print_function, unicode_literals

from schematics.models import Model
from schematics.types import ModelType, DictType, IntType, ListType, StringType

from cipy.validation.sanitizers import sanitize_integer, sanitize_string, sanitize_type


FIELD_SANITIZERS = {
    'review_id': lambda x: sanitize_integer(x, min_value=0, max_value=2147483647),
    'objective': sanitize_string,
    'pico': lambda x: {key: sanitize_string(val) for key, val in x.items()},
    'label': lambda x: sanitize_string(x, max_length=25),
    'question': lambda x: sanitize_string(x, max_length=500),
    'rank': lambda x: sanitize_integer(x, min_value=0, max_value=25),
    'term': lambda x: sanitize_string(x, max_length=100),
    'synonyms': lambda x: [sanitize_string(item, max_length=100)
                           for item in x],
    'group': lambda x: sanitize_string(x, max_length=100),
    'label': lambda x: sanitize_string(x, max_length=25),
    'explanation': sanitize_string
    }


def sanitize(record):
    """
    After parsing but before creating a `ReviewPlan` model, sanitize the values
    in a review plan `record` so that they'll pass validation.

    Args:
        record (dict)

    Returns:
        dict
    """
    list_keys = {'research_questions', 'keyterms', 'selection_criteria'}
    sanitized_record = {}
    for key, value in record.items():
        if key in list_keys and value:
            sanitized_record[key] = [{subkey: FIELD_SANITIZERS[subkey](subvalue)
                                      for subkey, subvalue in item.items()}
                                     for item in value]
        elif value:
            sanitized_record[key] = FIELD_SANITIZERS[key](value)
    return sanitized_record


class ResearchQuestion(Model):
    question = StringType(required=True, max_length=500)
    rank = IntType(required=True, min_value=0, max_value=25)


class Keyterm(Model):
    group = StringType(required=True, max_length=100)
    term = StringType(required=True, max_length=100)
    synonyms = ListType(StringType(max_length=100))


class SelectionCriterion(Model):
    label = StringType(required=True, max_length=25)
    explanation = StringType()


class ReviewPlan(Model):
    review_id = IntType(required=True,
                        min_value=0, max_value=2147483647)
    objective = StringType()
    research_questions = ListType(ModelType(ResearchQuestion))
    pico = DictType(StringType)
    keyterms = ListType(ModelType(Keyterm))
    selection_criteria = ListType(ModelType(SelectionCriterion))
