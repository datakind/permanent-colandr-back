from __future__ import absolute_import, division, print_function, unicode_literals

import io
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import (convert_to_unicode,
                                        author as sanitize_author_field)


# TODO: rename fields to be consistent with RIS a la tag_key_map???
# TODO: split 'references' field value by '; ' if it works consistently


def sanitize_record(record):
    record = remove_null_fields(record)
    record = convert_to_unicode(record)
    record = sanitize_type_field(record)
    record = sanitize_keyword_field(record)
    record = sanitize_pages_field(record)
    record = sanitize_author_field(record)
    return record


def remove_null_fields(record):
    return {key: value for key, value in record.items()
            if value}


def sanitize_type_field(record):
    if 'type' in record:
        record['type'] = record['type'].lower()
    return record


def sanitize_keyword_field(record, sep=',|;'):
    if 'keyword' in record:
        record['keyword'] = [i.strip() for i in
                             re.split(sep, record['keyword'].replace('\n', ''))]
    if 'author_keywords' in record:
        record['author_keywords'] = [i.strip() for i in
                                     re.split(sep, record['author_keywords'].replace('\n', ''))]
    return record


def sanitize_pages_field(record):
    if 'pages' in record:
        # hyphen, non-breaking hyphen, en dash, em dash, hyphen-minus, minus sign
        separators = ('‐', '‑', '–', '—', '-', '−')
        for sep in separators:
            if sep in record['pages']:
                pages = [i.strip().strip(sep)
                         for i in record['pages'].split(sep)
                         if i]
                if len(pages) > 2:
                    print('unusual "pages" field value: {}', record['pages'])
                record['pages'] = pages[0] + '--' + pages[-1]
                break
    return record


class BibTexFile(object):
    """
    Args:
        path (str): BibTex file to be parsed
        sanitizer (func): function that takes in a record (dict) and exports the
            same record (dict), modified according to user's needs
    """

    def __init__(self, path, sanitizer=None):
        self.path = path
        if sanitizer is None:
            sanitizer = sanitize_record
        self.parser = BibTexParser()
        self.parser.ignore_nonstandard_types = False
        self.parser.homogenize_fields = False
        self.parser.customization = sanitizer

    def parse(self):
        """
        Yields:
            dict: next parsed citation record
        """
        with io.open(self.path, mode='rt') as f:
            parsed_data = bibtexparser.load(f, parser=self.parser)
        for record in parsed_data.entries:
            yield record
