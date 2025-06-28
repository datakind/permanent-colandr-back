import csv
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
        "author": "authors",
        "editor": "editors",
        "keyword": "keywords",
        "journal": "journal_name",
        "month": "pub_month",
        "note": "notes",
        "number": "issue_number",
        "year": "pub_year",
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
            reader = csv.DictReader(f, self.dialect, delimiter=self.delimiter)
            for row in reader:
                yield row

    def sanitize(self, records: Iterable[dict]) -> Iterable[dict]:
        for record in records:
            record = self._standardize_field_names(record)
            yield record
