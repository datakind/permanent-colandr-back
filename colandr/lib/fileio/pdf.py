import pathlib

import pymupdf


def read(file_path: str | pathlib.Path) -> str:
    """Extract text from a PDF file and write it to a text file."""
    with pymupdf.open(str(file_path), filetype="pdf") as doc:
        # despite the docs, "sort" doesn't actually do what we want, so set to False
        text = chr(12).join(page.get_text("text", sort=False) for page in doc.pages())
    return text
