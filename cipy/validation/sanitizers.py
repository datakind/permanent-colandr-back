
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
