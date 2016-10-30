from . import constants


def sanitize_type(value, type_):
    """Return `value` cast as type `type`; None otherwise."""
    try:
        casted_value = type_(value)
    except (ValueError, TypeError):
        return None
    return casted_value


def sanitize_integer(value, min_value=None, max_value=None):
    """Return `value` as an int with `min_value` <= value <= `max_value`; None otherwise."""
    if not isinstance(value, int):
        value = sanitize_type(value, float)
        value = sanitize_type(value, int)
    if value is not None and min_value is not None:
        value = value if value >= min_value else None
    if value is not None and max_value is not None:
        value = value if value <= max_value else None
    return value


def sanitize_float(value, min_value=None, max_value=None):
    if not isinstance(value, float):
        value = sanitize_type(value, float)
    if value is not None and min_value is not None:
        value = value if value >= min_value else None
    if value is not None and max_value is not None:
        value = value if value <= max_value else None
    return value


def sanitize_string(value, max_length=None, truncate=True):
    """Return `value` as a str with len(value) <= `max_length` or, if `truncate`
    is True, as value[:max_length]; None otherwise."""
    value = sanitize_type(value, str)
    if value is not None and max_length is not None and len(value) > max_length:
        if truncate:
            value = value[:max_length]
        else:
            value = None
    return value


CITATION_FIELD_SANITIZERS = {
    'review_id': lambda x: sanitize_integer(x, min_value=0, max_value=constants.MAX_INT),
    'status': sanitize_string,
    'type_of_work': lambda x: sanitize_string(x, max_length=25),
    'title': lambda x: sanitize_string(x, max_length=300),
    'secondary_title': lambda x: sanitize_string(x, max_length=300),
    'abstract': sanitize_string,
    'pub_year': lambda x: sanitize_integer(x, max_value=constants.MAX_SMALLINT),
    'pub_month': lambda x: sanitize_integer(x, max_value=constants.MAX_SMALLINT),
    'authors': lambda x: [sanitize_string(item, max_length=100) for item in x],
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
