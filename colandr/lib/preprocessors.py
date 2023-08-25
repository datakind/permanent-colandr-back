import logging
import pathlib
from typing import BinaryIO

from ..apis import schemas
from . import fileio, sanitizers


LOGGER = logging.getLogger(__name__)


def preprocess_citations(
    path_or_stream: BinaryIO | pathlib.Path, fname: str, review_id: int
) -> list[dict]:
    if fname.endswith(".bib"):
        try:
            records = fileio.bibtex.read(path_or_stream)
        except Exception:
            raise ValueError(f"unable to parse BibTex citations file: '{fname}'")
    elif fname.endswith(".ris") or fname.endswith(".txt"):
        try:
            records = fileio.ris.read(path_or_stream)
        except Exception:
            raise ValueError(f"unable to parse RIS citations file: '{fname}'")
    else:
        raise ValueError(f"unknown file type: '{fname}'")

    citations = []
    sanitizer = sanitizers.sanitize_citation
    schema = schemas.CitationSchema()
    for record in records:
        record["review_id"] = review_id
        try:
            sanitized_record = sanitizer(record)
            citation = schema.load(sanitized_record)
            citations.append(citation)
        except Exception as e:
            LOGGER.warning("unable to parse citation; skipping... %s", e)
            pass

    return citations
