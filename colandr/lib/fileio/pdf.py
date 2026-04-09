import io
import pathlib
import typing as t

import pymupdf


def read(
    *,
    file_path: t.Optional[str | pathlib.Path] = None,
    stream: t.Optional[bytes | io.BytesIO] = None,
    redact_tables: bool = False,
) -> str:
    """
    Extract text from a PDF file, optionally redacting tables so they're not included.

    Args:
        file_path
        stream
        redact_tables
    """
    page_texts = []
    with pymupdf.open(filename=file_path, stream=stream, filetype="pdf") as doc:
        for page in doc.pages():
            # assert isinstance(page, pymupdf.Page)  # type guard
            if redact_tables:
                for table in page.find_tables():
                    # wrap table in a redaction annotation
                    page.add_redact_annot(table.bbox)
                # erase all table text
                page.apply_redactions()
            # despite the docs, "sort" doesn't actually do what we want, so set to False
            page_text = page.get_text("text", sort=False)
            page_texts.append(page_text)
    return chr(12).join(page_texts)
