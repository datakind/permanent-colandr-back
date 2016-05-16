from __future__ import absolute_import, division, print_function, unicode_literals

import io
import re

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode, getnames

# TODO: confirm that 'references' sanitization is correct

KEY_MAP = {
    'address': 'publisher_address',
    'author': 'authors',
    'keyword': 'keywords',
    'journal': 'journal_name',
    'month': 'publication_month',
    'note': 'notes',
    'number': 'issue_number',
    'publisher': 'publisher_name',
    'year': 'publication_year',
}

VALUE_SANITIZERS = {
    'author': lambda x: tuple(sorted(getnames([a.strip() for a in x.replace('\n', ' ').split(' and ')]))),
    'keyword': lambda x: tuple(sorted(kw.strip() for kw in re.split(r',|;', x.replace('\n', '')) if kw)),
    'author_keywords': lambda x: tuple(sorted(kw.strip() for kw in re.split(r',|;', x.replace('\n', '')) if kw)),
    'month': lambda x: int(x),
    'pages': lambda x: _sanitize_pages(x),
    'references': lambda x: tuple(sorted(ref.strip() for ref in x.split('; ') if ref)),
    'type': lambda x: x.lower(),
    'year': lambda x: int(x),
}


def _sanitize_pages(value):
    # hyphen, non-breaking hyphen, en dash, em dash, hyphen-minus, minus sign
    separators = ('‐', '‑', '–', '—', '-', '−')
    for sep in separators:
        if sep in value:
            pages = [i.strip().strip(sep)
                     for i in value.split(sep)
                     if i]
            if len(pages) > 2:
                print('unusual "pages" field value: {}', value)
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
                    except Exception:
                        print('value sanitization error: key={}, value={}'.format(key, value))
            if self.key_map:
                for key, rekey in self.key_map.items():
                    try:
                        record[rekey] = record.pop(key)
                    except KeyError:
                        pass

            yield record
