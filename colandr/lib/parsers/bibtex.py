from __future__ import absolute_import, division, print_function, unicode_literals

import io
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode, getnames

from .. import utils


# TODO: confirm that 'references' sanitization is correct

logger = utils.get_console_logger(__name__)

WHITESPACE_RE = re.compile(r"\s+")
_MONTH_MAP = {
    "spr": 3,
    "sum": 6,
    "fal": 9,
    "win": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}


def _sanitize_month(value):
    try:
        return int(value)
    except ValueError:
        value = (
            value.split(" ")[0].strip().lower()
            if " " in value
            else value.split("-")[0].strip().lower()
            if "-" in value
            else value.lower()
        )
        try:
            return _MONTH_MAP[value]
        except KeyError:
            raise ValueError


def _sanitize_pages(value):
    # hyphen, non-breaking hyphen, minus sign, en dash, em dash, hyphen-minus
    separators = ("‐", "‑", "−", "–", "—", "-")
    for sep in separators:
        if sep in value:
            pages = [i.strip().strip(sep) for i in value.split(sep) if i]
            if len(pages) > 2 or not pages:
                logger.debug('unusual "pages" field value: %s', value)
            elif len(pages) == 2:
                value = pages[0] + "--" + pages[-1]
                break
            else:
                value = pages[0]
                break
    return value


def _sanitize_record(record):
    record = {key: value for key, value in record.items() if value}
    record = convert_to_unicode(record)
    return record


KEY_MAP = {
    "document_type": "type_of_work",
    "ID": "reference_id",
    "address": "publisher_address",
    "author": "authors",
    "editor": "editors",
    "keyword": "keywords",
    "journal": "journal_name",
    "month": "pub_month",
    "note": "notes",
    "number": "issue_number",
    "year": "pub_year",
}

VALUE_SANITIZERS = {
    "author": lambda x: tuple(
        sorted(getnames([a.strip() for a in x.replace("\n", " ").split(" and ")]))
    ),
    "abstract": lambda x: WHITESPACE_RE.sub(" ", x),
    "document_type": lambda x: x.lower(),
    "keyword": lambda x: tuple(
        sorted(kw.strip() for kw in re.split(r",|;", x.replace("\n", "")) if kw)
    ),
    "author_keywords": lambda x: tuple(
        sorted(kw.strip() for kw in re.split(r",|;", x.replace("\n", "")) if kw)
    ),
    "month": _sanitize_month,
    "pages": _sanitize_pages,
    "references": lambda x: tuple(sorted(ref.strip() for ref in x.split("; ") if ref)),
    "title": lambda x: x.replace("\n", " "),
    "type": lambda x: x.lower(),
    "year": int,
}


class BibTexFile(object):
    """
    Args:
        path_or_stream (str or io stream): RIS file to be parsed, either as its
            path on disk or as a stream of data
        key_map (dict or bool): mapping of default BibTex tags to to human-readable keys;
            if None (default), default mapping is used; if False, no mapping will be done
        value_sanitizers (dict or bool): mapping of default BibTex tags to functions
            that sanitize their associated values; if None (default), default sanitizers
            will be used; if False, no sanitization will be performed
    """

    def __init__(self, path_or_stream, key_map=None, value_sanitizers=None):
        if isinstance(path_or_stream, io.TextIOBase):  # io.StringIO):
            self.path = None
            self.stream = path_or_stream
        elif isinstance(path_or_stream, io.IOBase):  # (io.BytesIO, io.BufferedRandom)):
            self.path = None
            self.stream = io.TextIOWrapper(path_or_stream)  # , encoding='utf8')
        elif isinstance(path_or_stream, (bytes, str)):
            self.path = path_or_stream
            self.stream = None
        self.parser = BibTexParser()
        self.parser.ignore_nonstandard_types = False
        self.parser.homogenize_fields = False
        self.parser.customization = _sanitize_record
        self.key_map = key_map if key_map is not None else KEY_MAP
        self.value_sanitizers = (
            value_sanitizers if value_sanitizers is not None else VALUE_SANITIZERS
        )

    def parse(self):
        """
        Yields:
            dict: next parsed citation record
        """
        if not self.stream:
            self.stream = io.open(self.path, mode="rt")
        with self.stream as f:
            parsed_data = bibtexparser.load(f, parser=self.parser)
        for record in parsed_data.entries:
            if self.value_sanitizers:
                for key, value in record.items():
                    try:
                        record[key] = self.value_sanitizers[key](value)
                    except KeyError:
                        pass
                    except TypeError:
                        logger.exception(
                            "value sanitization error: key=%s, value=%s", key, value
                        )
            if self.key_map:
                for key, rekey in self.key_map.items():
                    try:
                        record[rekey] = record.pop(key)
                    except KeyError:
                        pass

            yield record
