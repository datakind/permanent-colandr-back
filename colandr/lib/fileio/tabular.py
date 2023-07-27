from __future__ import annotations

import csv
import io
from collections.abc import Iterable


def read(data: str, *, dialect: str = "excel", **kwargs) -> Iterable[list[str]]:
    with io.StringIO(data) as f:
        reader = csv.reader(f, dialect, **kwargs)
        for row in reader:
            yield row


def write(
    cols: list[str], rows: Iterable[dict] | Iterable[list], *, dialect="excel", **kwargs
) -> str:
    f = io.StringIO()
    writer = csv.writer(f, dialect, **kwargs)
    writer.writerow(cols)
    writer.writerows(rows)
    return f.getvalue()


def write_iter(
    cols: list[str], rows: Iterable[dict] | Iterable[list], *, dialect="excel", **kwargs
) -> Iterable[str]:
    writer = csv.writer(DummyWriter(), dialect, **kwargs)
    yield writer.writerow(cols)
    for row in rows:
        yield writer.writerow(row)


class DummyWriter:
    def write(self, line):
        return line
