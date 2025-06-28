import abc
import datetime
import io
import logging
import pathlib
import tempfile
import typing as t
from collections.abc import Iterable, Sequence


LOGGER = logging.getLogger(__name__)


class BaseReader:
    """
    Base reader for a file or stream of "studies", containing typical reference info
    formatted in a standard format.

    Attributes:
        file_extensions
        field_alt_names
        field_sanitizers
    """

    file_extensions: set[str]
    field_alt_names: dict[str, Sequence[str]] | dict[str, str]
    field_sanitizers: dict[str, Sequence[t.Callable]]

    @abc.abstractmethod
    def read(
        self,
        path_or_stream: str | pathlib.Path | t.IO[bytes],
        encodings: Sequence[str] = ("utf-8", "utf-8-sig", "ISO-8859-1"),
    ) -> Iterable[dict]:
        """
        Read data from a file path or binary stream, trying ``encodings`` in order
        until successful; parse data format as needed into a sequence of records.

        Args:
            path_or_stream
            encodings
        """
        ...

    @abc.abstractmethod
    def sanitize(self, records: Iterable[dict]) -> Iterable[dict[str, object]]:
        """
        "Sanitize" raw records so they conform to a standard spec, by renaming fields,
        coercing dtypes, deriving new fields, etc.

        Args:
            records: As output by :meth:`BaseReader.read()` .
        """
        ...

    def _from_path_or_stream(
        self, path_or_stream: str | pathlib.Path | t.IO[bytes], encodings: Sequence[str]
    ) -> str:
        if not isinstance(
            path_or_stream,
            (str, pathlib.Path, io.BytesIO, tempfile.SpooledTemporaryFile),
        ):
            raise TypeError(
                "unable to read data from input path/stream: expected Path or IO[bytes], "
                f"got {type(path_or_stream)}"
            )

        data = None
        for encoding in encodings:
            try:
                if isinstance(path_or_stream, (str, pathlib.Path)):
                    data = self._from_path(path_or_stream, encoding)
                else:
                    data = self._from_stream(path_or_stream, encoding)
                break
            except UnicodeDecodeError:
                LOGGER.warning(
                    "unable to read data from input path/stream with encoding='%s'",
                    path_or_stream,
                    encoding,
                )
                continue
            except IOError:
                LOGGER.error(
                    "unable to read data from file='%s': file doesn't exist",
                    path_or_stream,
                )
                raise
        else:
            raise ValueError(
                "unable to read data from input path/stream"
                f"using any encoding in {encodings}"
            )
        return data

    def _from_path(self, path: str | pathlib.Path, encoding: str) -> str:
        path = pathlib.Path(path) if isinstance(path, str) else path
        if self.file_extensions and path.suffix not in self.file_extensions:
            raise IOError(
                f"unable to read file: expected extension in {self.file_extensions}, "
                f"got '{path.suffix}'"
            )

        with path.open(mode="r", encoding=encoding) as f:
            data = f.read()
        return data

    def _from_stream(self, stream: t.IO[bytes], encoding: str) -> str:
        data = io.TextIOWrapper(stream, encoding=encoding).read()
        # in PY3.10 and earlier, extra handling was needed; leaving here for ref
        # records = io.TextIOWrapper(
        #     io.BytesIO(stream.read()), encoding=encoding
        # ).read()
        return data

    def _standardize_field_names(self, record: dict[str, object]) -> dict[str, object]:
        record = {key.lower(): value for key, value in record.items()}
        if self.field_alt_names:
            # only one alt name per field? take this faster path
            if any(isinstance(val, str) for val in self.field_alt_names.values()):
                record = {self.field_alt_names.get(k, k): v for k, v in record.items()}  # type: ignore
            else:
                for name, alt_names in self.field_alt_names.items():
                    if name not in record:
                        for alt_name in alt_names:
                            if alt_name in record:
                                record[name] = record.pop(alt_name)
                                break
        return record

    def _sanitize_field_values(self, record: dict[str, object]) -> dict[str, object]:
        if self.field_sanitizers:
            for field, sanitizers in self.field_sanitizers.items():
                if field in record:
                    value = record[field]
                    for sanitizer in sanitizers:
                        value = sanitizer(value)
                    record[field] = value
        return record


# TODO
class BaseWriter:
    def write(self, records: Iterable[dict]) -> None: ...


def to_dttm(
    value: datetime.datetime | datetime.date | float | int | str,
) -> t.Optional[datetime.datetime]:
    """Cast ``value`` into a dttm, as able."""
    if isinstance(value, datetime.datetime):
        return value
    elif isinstance(value, datetime.date):
        return datetime.datetime(value.year, value.month, value.day)
    elif isinstance(value, str):
        try:
            return datetime.datetime.fromisoformat(value)
        except ValueError:
            for fmt in ("%m/%d/%Y", "%d/%m/%Y"):
                try:
                    return datetime.datetime.strptime(value, fmt)
                except ValueError:
                    pass
    elif isinstance(value, (float, int)):
        try:
            return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
        except Exception:
            pass

    LOGGER.debug("unable to cast '%s' into a dttm", value)
    return None


def to_int(value: float | int | str) -> t.Optional[int]:
    """Cast ``value`` into an int, as able."""
    if isinstance(value, int):
        return value
    else:
        try:
            return int(float(value))
        except ValueError:
            LOGGER.debug("unable to cast '%s' into an int", value)
            return None


def to_list(value: object) -> list:
    """Cast ``value`` into a list, as able."""
    if isinstance(value, list):
        return value
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return list(value)
    else:
        return [value]
