import csv
import io
import itertools
import typing as t
from collections.abc import Iterable, Sequence


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


def write_stream(
    cols: Sequence[str],
    rows: Iterable[dict[str, t.Any]] | Iterable[list],
    *,
    dialect="excel",
    **kwargs,
) -> Iterable[str]:
    """
    Write tabular data (rows x cols) in CSV format, in-memory, streaming row-by-row.

    Reference:
        https://stackoverflow.com/questions/32608265/streaming-a-generated-csv-with-flask
    """
    first_row = next(iter(rows))
    rows_ = itertools.chain([first_row], rows)
    if isinstance(first_row, dict):
        writer = csv.DictWriter(DummyWriter(), cols, dialect=dialect, **kwargs)
        yield writer.writeheader()
        for row in rows_:
            yield writer.writerow(row)
    else:
        writer = csv.writer(DummyWriter(), dialect, **kwargs)
        yield writer.writerow(cols)
        for row in rows:
            yield writer.writerow(row)


class DummyWriter:
    def write(self, line):
        return line
