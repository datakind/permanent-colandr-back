import typing as t

from . import constants


def sanitize_citation(record: dict[str, t.Any]) -> dict[str, t.Any]:
    """
    Sanitize keys/values of a 'raw' citation record into something suitable
    for insertion into the corresponding database table.
    """
    sanitized_record = {
        "review_id": sanitize_integer(
            record.get("review_id"), min_value=0, max_value=constants.MAX_INT
        ),
        "type_of_work": sanitize_string(record.get("type_of_work"), max_length=25),
        "title": sanitize_string(record.get("title"), max_length=300),
        "secondary_title": sanitize_string(
            record.get("secondary_title"), max_length=300
        ),
        "abstract": sanitize_string(record.get("abstract")),
        "pub_year": sanitize_integer(
            record.get("pub_year"), max_value=constants.MAX_SMALLINT
        ),
        "pub_month": sanitize_integer(
            record.get("pub_month"), max_value=constants.MAX_SMALLINT
        ),
        "authors": [
            sanitize_string(item, max_length=100) for item in record.get("authors", [])
        ],
        "keywords": [
            sanitize_string(item, max_length=100) for item in record.get("keywords", [])
        ],
        "type_of_reference": sanitize_string(
            record.get("type_of_reference"), max_length=50
        ),
        "journal_name": sanitize_string(record.get("journal_name"), max_length=100),
        "volume": sanitize_string(record.get("volume"), max_length=20),
        "issue_number": sanitize_string(record.get("issue_number"), max_length=20),
        "doi": sanitize_string(record.get("doi"), max_length=100),
        "issn": sanitize_string(record.get("issn"), max_length=20),
        "publisher": sanitize_string(record.get("publisher"), max_length=100),
        "language": sanitize_string(record.get("language"), max_length=50),
    }
    # put all other fields into a nested dict with string/null values
    sanitized_record["other_fields"] = {
        key: sanitize_type(value, str)
        for key, value in record.items()
        if key not in sanitized_record
    }
    return sanitized_record


def sanitize_type(value, type_):
    """Return `value` cast as type `type`; None otherwise."""
    if value is None:
        return None
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
