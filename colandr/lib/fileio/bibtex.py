import logging
import pathlib
import re
from typing import Dict, List, Optional, TextIO, Tuple, Union

import bibtexparser


LOGGER = logging.getLogger(__name__)

RE_NAME_SPLIT = re.compile(r" and ", flags=re.IGNORECASE)

INT_KEYS = ("end_page", "number_of_pages", "pub_year", "start_page")

MONTH_TO_INT = {
    "spr": 3,
    "sum": 6,
    "fal": 9,
    "win": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}

DEFAULT_TO_SANITIZED_KEYS = {
    # "document_type": "type_of_work",
    "ENTRYTYPE": "type_of_work",
    "ID": "reference_id",
    # "address": "publisher_address",
    "author": "authors",
    "editor": "editors",
    "keyword": "keywords",
    "journal": "journal_name",
    "month": "pub_month",
    "note": "notes",
    "number": "issue_number",
    "year": "pub_year",
}


def read(path_or_stream: Union[TextIO, pathlib.Path]) -> List[Dict]:
    for encoding in ["utf-8", "ISO-8859-1"]:
        try:
            with path_or_stream.open(mode="r", encoding=encoding) as f:
                data = f.read()
            break
        except UnicodeDecodeError:
            pass
        except IOError as e:
            LOGGER.warning(e)
    else:
        raise ValueError("unable to parse input BiBTex data")

    records = parse(data)
    records = sanitize(records)
    return records


def parse(data: str) -> List[Dict]:
    parser = bibtexparser.bparser.BibTexParser(
        ignore_nonstandard_types=False,
        homogenize_fields=True,
        common_strings=True,
        interpolate_strings=True,
        customization=_parser_customization,
    )
    bib_db = bibtexparser.loads(data, parser=parser)
    return bib_db.entries


def sanitize(records: List[Dict]) -> List[Dict]:
    return [_sanitize_record(record) for record in records]


def _sanitize_record(record: dict) -> dict:
    # standardize key names
    record = {DEFAULT_TO_SANITIZED_KEYS.get(k, k): v for k, v in record.items()}
    if "pub_month" in record:
        record["pub_month"] = _sanitize_month(record["pub_month"])
    if "pages" in record:
        pages = _try_to_int(record["pages"])
        if pages is not None:
            record["number_of_pages"] = pages
        else:
            pages = _split_pages(record["pages"])
            if pages is not None:
                record["start_page"] = pages[0]
                record["end_page"] = pages[1]
        del record["pages"]
    # try to cast certain values to more specific dtypes
    record.update({key: _try_to_int(record[key]) for key in INT_KEYS if key in record})
    return record


def _parser_customization(record: dict) -> dict:
    record = bibtexparser.customization.convert_to_unicode(record)
    record = _split_names(record, "author")
    record = _split_names(record, "editor")
    record = bibtexparser.customization.keyword(record, sep=",|;")
    record = bibtexparser.customization.page_double_hyphen(record)
    return record


def _split_names(record: dict, field_name: str) -> dict:
    """
    Split field into a list of "Name, Surname" values.
    Modified from :func:`bibtexparser.customization.author()` .
    """
    if field_name in record and record[field_name]:
        value = record[field_name].replace("\n", " ")
        record[field_name] = bibtexparser.customization.getnames(
            [name.strip() for name in RE_NAME_SPLIT.split(value)]
        )
    return record


def _sanitize_month(value: str) -> Optional[int]:
    try:
        return int(value)
    except ValueError:
        value = value.strip()[:3].lower()
        try:
            return MONTH_TO_INT[value]
        except KeyError:
            return None


def _try_to_int(int_maybe: str) -> Optional[int]:
    try:
        return int(int_maybe)
    except ValueError:
        LOGGER.debug("unable to cast '%s' into an int", int_maybe)
        return None


def _split_pages(value: str) -> Optional[Tuple[int, int]]:
    if "--" in value:
        pages = value.split("--")
        if len(pages) == 2:
            start_page, end_page = pages
            return (_try_to_int(start_page), _try_to_int(end_page))
    LOGGER.warning("unable to sanitize pages='%s' value", value)
    return None
