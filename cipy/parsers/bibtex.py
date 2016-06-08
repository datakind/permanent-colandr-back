from __future__ import absolute_import, division, print_function, unicode_literals

import io
import logging
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode, getnames

# TODO: confirm that 'references' sanitization is correct

LOGGER = logging.getLogger(__name__)

_MONTH_MAP = {'spr': 3, 'sum': 6, 'fal': 9, 'win': 12,
              'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
              'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

def _sanitize_month(value):
    try:
        return int(value)
    except ValueError:
        value = value.split(' ')[0].strip().lower() if ' ' in value \
                else value.split('-')[0].strip().lower() if '-' in value \
                else value.lower()
        try:
            return _MONTH_MAP[value]
        except KeyError:
            raise ValueError


def _sanitize_pages(value):
    # hyphen, non-breaking hyphen, en dash, em dash, hyphen-minus, minus sign
    separators = ('‐', '‑', '–', '—', '-', '−')
    for sep in separators:
        if sep in value:
            pages = [i.strip().strip(sep)
                     for i in value.split(sep)
                     if i]
            if len(pages) > 2:
                LOGGER.debug('unusual "pages" field value: %s', value)
            else:
                value = pages[0] + '--' + pages[-1]
                break
    return value


def _sanitize_record(record):
    record = {key: value
              for key, value in record.items()
              if value}
    record = convert_to_unicode(record)
    return record


KEY_MAP = {
    'document_type': 'type_of_work',
    'ID': 'reference_id',
    'address': 'publisher_address',
    'author': 'authors',
    'keyword': 'keywords',
    'journal': 'journal_name',
    'month': 'publication_month',
    'note': 'notes',
    'number': 'issue_number',
    'year': 'publication_year',
}

VALUE_SANITIZERS = {
    'author': lambda x: tuple(sorted(getnames([a.strip() for a in x.replace('\n', ' ').split(' and ')]))),
    'document_type': lambda x: x.lower(),
    'keyword': lambda x: tuple(sorted(kw.strip() for kw in re.split(r',|;', x.replace('\n', '')) if kw)),
    'author_keywords': lambda x: tuple(sorted(kw.strip() for kw in re.split(r',|;', x.replace('\n', '')) if kw)),
    'month': _sanitize_month,
    'pages': _sanitize_pages,
    'references': lambda x: tuple(sorted(ref.strip() for ref in x.split('; ') if ref)),
    'type': lambda x: x.lower(),
    'year': int,
}


class BibTexFile(object):
    """
    Args:
        path (str): BibTex file to be parsed
        key_map (dict or bool): mapping of default BibTex tags to to human-readable keys;
            if None (default), default mapping is used; if False, no mapping will be done
        value_sanitizers (dict or bool): mapping of default BibTex tags to functions
            that sanitize their associated values; if None (default), default sanitizers
            will be used; if False, no sanitization will be performed
    """

    def __init__(self, path, key_map=None, value_sanitizers=None):
        self.path = path
        self.parser = BibTexParser()
        self.parser.ignore_nonstandard_types = False
        self.parser.homogenize_fields = False
        self.parser.customization = _sanitize_record
        self.key_map = (key_map if key_map is not None
                        else KEY_MAP)
        self.value_sanitizers = (value_sanitizers if value_sanitizers is not None
                                 else VALUE_SANITIZERS)

    def parse(self):
        """
        Yields:
            dict: next parsed citation record
        """
        with io.open(self.path, mode='rt') as f:
            parsed_data = bibtexparser.load(f, parser=self.parser)
        for record in parsed_data.entries:
            if self.value_sanitizers:
                for key, value in record.items():
                    try:
                        record[key] = self.value_sanitizers[key](value)
                    except KeyError:
                        pass
                    except TypeError:
                        LOGGER.exception('value sanitization error: key=%s, value=%s',
                            key, value)
            if self.key_map:
                for key, rekey in self.key_map.items():
                    try:
                        record[rekey] = record.pop(key)
                    except KeyError:
                        pass

            yield record
