import datetime
import io
import logging
import pathlib
import tempfile
import typing as t
from collections.abc import Iterable, Sequence

from dateutil.parser import ParserError
from dateutil.parser import parse as parse_dttm


LOGGER = logging.getLogger(__name__)


def load_from_path_or_stream(
    path_or_stream: t.BinaryIO | pathlib.Path,
    encodings: Sequence[str] = ("utf-8", "ISO-8859-1"),
) -> str:
    """
    Load data from a file path or binary stream, trying ``encodings`` in sequential order
    until a successful match is found; otherwise, raise an error.

    Args:
        path_or_stream
        encodings
    """
    for encoding in encodings:
        try:
            if isinstance(path_or_stream, pathlib.Path):
                with path_or_stream.open(mode="r", encoding=encoding) as f:
                    data = f.read()
            elif isinstance(path_or_stream, io.BytesIO):
                data = io.TextIOWrapper(path_or_stream, encoding=encoding).read()
            # HACK: apparently this got fixed in PY3.11,
            # for which case this next if block can probably be removed
            elif isinstance(path_or_stream, tempfile.SpooledTemporaryFile):
                data = io.TextIOWrapper(
                    io.BytesIO(path_or_stream.read()), encoding=encoding
                ).read()
            else:
                raise TypeError(f"expected Path or BytesIO, got {type(path_or_stream)}")
            break
        except UnicodeDecodeError:
            pass
        except IOError:
            LOGGER.error(
                "unable to load data from path or stream %s -- does not exist!",
                path_or_stream,
            )
            raise
    else:
        raise ValueError(
            f"unable to load data from input path or stream '{path_or_stream}' "
            f"using any encodings in {encodings}"
        )

    return data


def try_to_dttm(value: float | int | str) -> t.Optional[datetime.datetime]:
    """Cast ``value`` into a dttm, as needed."""
    if isinstance(value, int):
        try:
            return datetime.datetime.fromtimestamp(value, tz=datetime.timezone.utc)
        except Exception:
            LOGGER.debug("unable to cast '%s' into a dttm", value)
    elif isinstance(value, str):
        try:
            return parse_dttm(value)
        except ParserError:
            LOGGER.debug("unable to cast '%s' into a dttm", value)
    else:
        LOGGER.debug("unable to cast '%s' into a dttm", value)
    return None


def try_to_int(value: float | int | str) -> t.Optional[int]:
    """Cast ``value`` into an int, as needed."""
    if isinstance(value, int):
        return value
    else:
        try:
            return int(float(value))
        except ValueError:
            LOGGER.debug("unable to cast '%s' into an int", value)
            return None


def to_list(value: t.Any) -> list:
    """Cast ``value`` into a list, as needed."""
    if isinstance(value, list):
        return value
    elif isinstance(value, Iterable) and not isinstance(value, (str, bytes)):
        return list(value)
    else:
        return [value]
