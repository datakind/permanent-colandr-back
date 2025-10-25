import csv
import datetime
import io
import logging
import pathlib
import typing as t
from collections.abc import Iterable, Sequence

from . import base


LOGGER = logging.getLogger(__name__)


class TabularReader(base.BaseReader):
    file_extensions = {".csv", ".tsv"}
    field_alt_names = {
        "abstract_note": "abstract",
        "author": "authors",
        "author/s": "authors",
        "date_published": "date",
        "document_type": "type_of_work",
        "editor": "editors",
        "index_keywords": "keywords",
        "item_type": "type_of_work",
        "keyword": "keywords",
        "journal": "journal_name",
        "month": "pub_month",
        "note": "notes",
        "num_pages": "number_of_pages",
        "number": "issue_number",
        "publication_title": "title",
        "publication_type": "type_of_work",
        "publication_year": "pub_year",
        "year": "pub_year",
    }
    field_sanitizers = {
        "authors": [lambda x: _split_concatenated_values(x)],
        "date": [base.to_dttm],
        "editors": [lambda x: _split_concatenated_values(x)],
        "end_page": [base.to_int],
        "keywords": [lambda x: _split_concatenated_values(x)],
        "number_of_pages": [base.to_int],
        "pub_year": [base.to_int],
        "start_page": [base.to_int],
    }

    def __init__(self, delimiter: str = ",", dialect: str = "excel"):
        self.delimiter = delimiter
        self.dialect = dialect

    def read(
        self,
        path_or_stream: str | pathlib.Path | t.IO[bytes],
        encodings: Sequence[str] = ("utf-8", "utf-8-sig", "ISO-8859-1"),
    ) -> Iterable[dict]:
        data = self._from_path_or_stream(path_or_stream, encodings)
        with io.StringIO(data) as f:
            reader = csv.DictReader(f, dialect=self.dialect, delimiter=self.delimiter)
            for row in reader:
                yield row

    def sanitize(self, records: Iterable[dict]) -> Iterable[dict]:
        for record in records:
            record = self._standardize_field_names(record)
            record = self._sanitize_field_values(record)
            if record.get("date"):
                assert isinstance(record["date"], datetime.datetime)  # type guard
                if not record.get("pub_year"):
                    record["pub_year"] = record["date"].year
                if not record.get("pub_month"):
                    record["pub_month"] = record["date"].month
                record["date"] = record["date"].strftime("%Y-%m-%d")
            yield record


def _split_concatenated_values(value: str, sep: str = ";") -> list[str]:
    values = value.split(sep)
    return [val.strip() for val in values]
