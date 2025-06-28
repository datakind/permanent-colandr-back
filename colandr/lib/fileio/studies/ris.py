"""
References:
    - https://github.com/asreview/citation-file-formatting/tree/main
    - https://en.wikipedia.org/wiki/RIS_(file_format)
"""

import logging
import pathlib
import typing as t
from collections.abc import Iterable, Sequence

import markupsafe
import rispy
import rispy.utils

from . import base


LOGGER = logging.getLogger(__name__)


class RisReader(base.BaseReader):
    file_extensions = {".ris", ".txt"}
    field_alt_names = {
        "abstract": ("notes_abstract", "abstract_note"),
        "authors": ("first_authors", "author names"),
        "journal_name": (
            "alternate_journal",
            "alternate_title3",
            "alternate_title2",
            "alternate_title1",
            "J1",
        ),
        "pub_year": ("publication_year", "year"),
        "title": ("primary_title", "short_title", "translated_title"),
    }
    ref_type_tag_overrides = {
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
            "subsidiary_authors": "translators",
            "tertiary_authors": "editors",
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
    reference_type_map = (
        {
            key: val.lower()
            for key, val in rispy.config.TYPE_OF_REFERENCE_MAPPING.items()
        }
        # override "BOOK" => "whole book", which is silly
        | {"BOOK": "book"}
    )
    field_sanitizers = {
        "access_date": [base.to_dttm],
        "authors": [lambda x: _split_up_authors(x)],
        "date": [base.to_dttm],
        "end_page": [base.to_int],
        "notes": [base.to_list, lambda x: _strip_tags_from_notes(x)],
        "number_of_pages": [base.to_int],
        "number_of_volumes": [base.to_int],
        "pub_year": [base.to_int],
        "start_page": [base.to_int],
        "year": [base.to_int],
    }

    def read(
        self,
        path_or_stream: str | pathlib.Path | t.IO[bytes],
        encodings: Sequence[str] = ("utf-8", "utf-8-sig", "ISO-8859-1"),
    ) -> Iterable[dict]:
        data = self._from_path_or_stream(path_or_stream, encodings)
        records = rispy.loads(
            data,
            implementation=rispy.parser.RisParser,
            skip_unknown_tags=False,
        )
        for record in records:
            yield record

    def sanitize(self, records: Iterable[dict]) -> Iterable[dict]:
        records = rispy.utils.convert_reference_types(
            list(records), type_map=self.reference_type_map
        )
        for record in records:
            yield self._sanitize_record(record)

    def _sanitize_record(self, record: dict) -> dict:
        # rename certain tags with their type-specific names
        if record.get("type_of_reference") in self.ref_type_tag_overrides:
            record = {
                self.ref_type_tag_overrides[record["type_of_reference"]].get(k, k): v
                for k, v in record.items()
            }
        # standardize all field names
        record = self._standardize_field_names(record)
        # sanitize values
        record = self._sanitize_field_values(record)
        # split date key into year (if needed) and month
        if record.get("date"):
            record["pub_month"] = record["date"].month
            if "pub_year" not in record:
                record["pub_year"] = record["date"].year
        # HACK: cast dttms to dt strings to avoid json encoding error
        record |= {
            key: record[key].strftime("%Y-%m-%d")
            for key in ("access_date", "date")
            if record.get(key)
        }
        return record


def _split_up_authors(authors: list[str]) -> list[str]:
    if len(authors) == 1:
        if authors[0].count(",") >= 2:
            authors = [author.strip() for author in authors[0].split(",")]
        elif authors[0].count(" ") >= 5:
            # TODO: this is probably bad data (all authors in one field w/o delimiters)
            # but how to reliably fix?
            pass
    return authors


def _strip_tags_from_notes(notes: list[str]) -> list[str]:
    notes = [markupsafe.Markup(note).striptags() for note in notes]
    return [note for note in notes if note]
