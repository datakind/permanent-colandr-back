"""
References:
    - https://www.bibtex.com/g/bibtex-format
    - https://en.wikipedia.org/wiki/BibTeX
"""

import logging
import pathlib
import re
import typing as t
from collections.abc import Iterable, Sequence

import bibtexparser

from . import base


LOGGER = logging.getLogger(__name__)

RE_NAME_SPLIT = re.compile(r" and ", flags=re.IGNORECASE)
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


def _split_names(value: str) -> list[str]:
    """
    Split field into a list of "Name, Surname" values.
    Modified from :func:`bibtexparser.customization.author()` .
    """
    value = value.replace("\n", " ")
    return bibtexparser.customization.getnames(
        [name.strip() for name in RE_NAME_SPLIT.split(value)]
    )


def _split_keywords(value: str, sep: str = ",|;") -> list[str]:
    """
    Split keyword into a list of values.
    Modified from :func:`bibtexparser.customization.keyword()` .
    """
    return [kw.strip() for line in value.split("\n") for kw in re.split(sep, line)]


def _sanitize_month(value: str) -> t.Optional[int]:
    try:
        return int(value)
    except ValueError:
        value = value.strip()[:3].lower()
        try:
            return MONTH_TO_INT[value]
        except KeyError:
            return None


def _split_pages(value: str) -> t.Optional[tuple[t.Optional[int], t.Optional[int]]]:
    if "--" in value:
        pages = value.split("--")
        if len(pages) == 2:
            start_page, end_page = pages
            return (base.to_int(start_page), base.to_int(end_page))

    LOGGER.warning("unable to sanitize pages='%s' value", value)
    return None


class BibTexReader(base.BaseReader):
    file_extensions = {".bib"}
    field_alt_names = {
        "entrytype": "type_of_work",
        "id": "reference_id",
        "author": "authors",
        "editor": "editors",
        "keyword": "keywords",
        "journal": "journal_name",
        "month": "pub_month",
        "note": "notes",
        "number": "issue_number",
        "year": "pub_year",
    }
    field_sanitizers = {
        "authors": [_split_names],
        "editors": [_split_names],
        "end_page": [base.to_int],
        "keywords": [_split_keywords],
        "notes": [base.to_list],
        "number_of_pages": [base.to_int],
        "pub_month": [_sanitize_month],
        "pub_year": [base.to_int],
        "start_page": [base.to_int],
    }

    def read(
        self,
        path_or_stream: str | pathlib.Path | t.IO[bytes],
        encodings: Sequence[str] = ("utf-8", "utf-8-sig", "ISO-8859-1"),
    ) -> Iterable[dict]:
        data = self._from_path_or_stream(path_or_stream, encodings)
        parser = bibtexparser.bparser.BibTexParser(
            ignore_nonstandard_types=False,
            homogenize_fields=True,
            common_strings=True,
            interpolate_strings=True,
            customization=self._parser_customization,
        )
        bib_db = bibtexparser.loads(data, parser=parser)
        for record in bib_db.entries:
            yield record

    def _parser_customization(self, record: dict) -> dict:
        record = bibtexparser.customization.convert_to_unicode(record)
        record = bibtexparser.customization.page_double_hyphen(record)
        return record

    def sanitize(self, records: Iterable[dict]) -> Iterable[dict]:
        for record in records:
            yield self._sanitize_record(record)

    def _sanitize_record(self, record: dict) -> dict:
        # standardize all field names
        record = self._standardize_field_names(record)
        # sanitize values
        record = self._sanitize_field_values(record)
        # parse pages into constituent parts (if present), and standardize naming
        if "pages" in record:
            # case: pages is just an int
            pages = base.to_int(record["pages"])
            if pages is not None:
                record["number_of_pages"] = pages
            # case: pages is a range of ints
            else:
                pages = _split_pages(record["pages"])
                if pages is not None:
                    record["start_page"] = pages[0]
                    record["end_page"] = pages[1]
            del record["pages"]
        return record
