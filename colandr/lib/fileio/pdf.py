import pathlib
from typing import Union

import fitz


def read(file_path: Union[str, pathlib.Path]) -> str:
    """Extract text from a PDF file and write it to a text file."""
    with fitz.open(str(file_path), filetype="pdf") as doc:
        text = chr(12).join(page.get_text("text", sort=True) for page in doc)
    return text
