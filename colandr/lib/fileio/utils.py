import io
import logging
import pathlib
from typing import BinaryIO, Sequence, Union

LOGGER = logging.getLogger(__name__)


def load_from_path_or_stream(
    path_or_stream: Union[BinaryIO, pathlib.Path],
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
