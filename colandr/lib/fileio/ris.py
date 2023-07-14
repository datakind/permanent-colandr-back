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

REF_TYPE_TAG_OVERRIDES = {
    "journal": {
        "alternate_title1": "alternate_journal",
        "custom7": "article_number",
        "edition": "epub_date",
        "M2": "start_page",
        "number": "issue_number",
        "secondary_title": "journal_name",
    },
    "book": {
        "issn": "isbn",
        "note": "series_volume",
        "secondary_authors": "series_editors",
        "secondary_title": "series_title",
        "start_page": "number_of_pages",
        "tertiary_authors": "editors",
        "subsidiary_authors": "translators",
    },
    "newspaper": {
        "custom1": "column",
        "custom2": "issue_number",
        "note": "start_page",
        "number_of_volumes": "frequency",
        "secondary_title": "newspaper",
    },
}
"""
Partial mapping of "raw" tag name to a type-specific tag name,
according to the 2011+ RIS specification.
Ref: https://github.com/aurimasv/translators/wiki/RIS-Tag-Map-(narrow)
"""

DTTM_KEYS = ("access_date", "date")
INT_KEYS = ("end_page", "number_of_volumes", "publication_year", "start_page", "year")

DEFAULT_TO_ALT_KEYS = {
    "journal_name": ("alternate_title3", "alternate_title2", "alternate_title1", "J1"),
    "publication_year": ("year",),
    "title": ("primary_title", "short_title", "translated_title"),
}


def parse(ris_data: Union[TextIO, pathlib.Path]) -> List[Dict]:
    for encoding in ["utf-8", "ISO-8859-1"]:
        try:
            return rispy.load(
                ris_data,
                encoding=encoding,
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
    # rename certain tags with their type-specific names
    if reference["type_of_reference"] in REF_TYPE_TAG_OVERRIDES:
        tag_overrides = REF_TYPE_TAG_OVERRIDES[reference["type_of_reference"]]
        reference = {tag_overrides.get(k, k): v for k, v in reference.items()}
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
