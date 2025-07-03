import pathlib

import pymupdf


def read(file_path: str | pathlib.Path) -> str:
    """Extract text from a PDF file and write it to a text file."""
    with pymupdf.open(str(file_path), filetype="pdf") as doc:
        text = chr(12).join(page.get_text("text", sort=True) for page in doc.pages())
    return text
