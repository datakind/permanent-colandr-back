import datetime
import logging
import pathlib
from typing import Dict, List, Optional, TextIO, Union

import rispy
import rispy.utils
from dateutil.parser import ParserError
from dateutil.parser import parse as parse_date


LOGGER = logging.getLogger(__name__)

TYPE_OF_REFERENCE_MAPPING = {
    key: val.lower() for key, val in rispy.config.TYPE_OF_REFERENCE_MAPPING.items()
}

DTTM_KEYS = ("access_date", "date")
INT_KEYS = ("end_page", "number_of_volumes", "publication_year", "start_page", "year")

DEFAULT_TO_ALT_KEYS = {
    "journal_name": ("alternate_title3", "alternate_title2", "alternate_title1", "J1"),
    "publication_year": ("year",),
    "title": ("primary_title", "short_title", "translated_title"),
}


def parse(file_path: Union[TextIO, pathlib.Path]) -> List[Dict]:
    for encoding in ["utf-8", "ISO-8859-1"]:
        try:
            return rispy.load(
                file_path,
                encoding=encoding,
                implementation=rispy.RisParser,
                skip_missing_tags=False,
                skip_unknown_tags=False,
            )
        except UnicodeDecodeError:
            pass
        except IOError as e:
            LOGGER.warning(e)
    else:
        raise ValueError("unable to parse input RIS data")


def sanitize(references: List[Dict]) -> List[Dict]:
    # convert reference types into human-readable equivalents
    # override "BOOK" => "whole book", which is silly
    type_map = {**TYPE_OF_REFERENCE_MAPPING, **{"BOOK": "book"}}
    references = rispy.utils.convert_reference_types(references, type_map=type_map)
    references = [_sanitize_reference(reference) for reference in references]
    return references


def _sanitize_reference(reference: dict) -> dict:
    # try to cast certain values to more specific dtypes
    reference.update(
        {key: _try_to_dttm(reference[key]) for key in DTTM_KEYS if key in reference}
    )
    reference.update(
        {key: _try_to_int(reference[key]) for key in INT_KEYS if key in reference}
    )
    # assign standardized fields in preferential key order
    for default_key, alt_keys in DEFAULT_TO_ALT_KEYS.items():
        if default_key not in reference:
            for alt_key in alt_keys:
                if alt_key in reference:
                    reference[default_key] = reference.pop(alt_key)
                    break
    # split date key into year (if needed) and month
    if "date" in reference:
        reference["pub_month"] = reference["date"].month
        if "pub_year" not in reference:
            reference["pub_year"] = reference["date"].year
    return reference


def _try_to_int(int_maybe: str) -> Optional[int]:
    try:
        return int(int_maybe)
    except ValueError:
        LOGGER.debug("unable to cast '%s' into an int", int_maybe)
        return None


def _try_to_dttm(dttm_maybe: str) -> Optional[datetime.datetime]:
    try:
        return parse_date(dttm_maybe)
    except ParserError:
        LOGGER.debug("unable to cast '%s' into a dttm", dttm_maybe)
        return None
