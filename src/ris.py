from __future__ import absolute_import, division, print_function, unicode_literals

import io
import re

from dateutil.parser import parse as parse_date


tag_key_map = {
    'A1': 'primary_authors',  # special: Lastname, Firstname, Suffix
    'A2': 'secondary_authors',  # special: Lastname, Firstname, Suffix
    'A3': 'tertiary_authors',  # special: Lastname, Firstname, Suffix
    'A4': 'subsidiary_authors',  # special: Lastname, Firstname, Suffix
    'AB': 'abstract',
    'AD': 'author_address',
    'AN': 'accession_number',
    'AU': 'authors',  # special
    'AV': 'location_in_archives',
    'BN': 'isbn',
    'BP': 'start_page',
    'BT': 'bt',
    'C1': 'custom_1',
    'C2': 'custom_2',
    'C3': 'custom_3',
    'C4': 'custom_4',
    'C5': 'custom_5',
    'C6': 'custom_6',
    'C7': 'custom_7',
    'C8': 'custom_8',
    'CA': 'caption',
    'CN': 'call_number',
    'CP': 'cp',
    'CT': 'title_of_unpublished_ref',
    'CY': 'place_published',
    'DA': 'date',  # special: YYYY, YYYY/MM, YYYY/MM/DD/, or YYYY/MM/DD/other info
    'DB': 'name_of_database',
    'DE': 'author_keywords',
    'DI': 'doi',
    'DO': 'doi',
    'DP': 'database_provider',
    'DT': 'document_type',
    'ED': 'editor',
    'EF': 'end_file',  # ignore!
    'EM': 'email_address',
    'EP': 'end_page',
    'ER': 'end_of_reference',  # special: must be empty and last tag of record
    'ET': 'edition',
    'FN': 'file_name',  # ignore!
    'ID': 'reference_id',
    'IS': 'issue_number',
    'J1': 'journal_name_user_abbr_1',
    'J2': 'journal_name_user_abbr_2',
    'JA': 'journal_name_abbr',
    'JF': 'journal_name',
    'JO': 'journal_name',
    'KW': 'keywords',  # special
    'L1': 'link_to_pdf',
    'L2': 'link_to_fulltext',
    'L3': 'related_records',
    'L4': 'figure',
    'LA': 'language',
    'LB': 'label',
    'LK': 'link_to_website',
    'M1': 'number',
    'M2': 'miscellaneous_2',
    'M3': 'type_of_work',
    'N1': 'notes',
    'N2': 'abstract',
    'NV': 'number_of_volumes',
    'OP': 'original_publication',
    'PB': 'publisher',
    'PD': 'publication_date',
    'PP': 'publishing_place',
    'PT': 'publication_type',
    'PY': 'publication_year',  # special: YYYY
    'RI': 'reviewed_item',
    'RN': 'research_notes',
    'RP': 'reprint_status',  # special: 'IN FILE', 'NOT IN FILE', or 'ON REQUEST (MM/DD/YY)'
    'SE': 'section',
    'SN': 'issn',
    'SO': 'source_name',
    'SP': 'start_page',
    'ST': 'short_title',
    'SU': 'supplement',
    'T1': 'primary_title',
    'T2': 'secondary_title',  # note: journal_title, if applicable
    'T3': 'tertiary_title',
    'TA': 'translated_author',
    'TC': 'times_cited',
    'TI': 'title',
    'TT': 'translated_title',
    'TY': 'type_of_reference',  # special: must be key in REFERENCE_TYPES and first tag of record
    'U1': 'user_defined_1',
    'U2': 'user_defined_2',
    'U3': 'user_defined_3',
    'U4': 'user_defined_4',
    'U5': 'user_defined_5',
    'UR': 'url',
    'UT': 'unique_identifier',
    'VL': 'volume',
    'VO': 'published_standard_number',
    'VR': 'version',  # ignore!
    'Y1': 'primary_date',  # special: YYYY/
    'Y2': 'access_date',
}

REFERENCE_TYPES_MAPPING = {
    'ABST': 'abstract',
    'ADVS': 'audiovisual material',
    'AGGR': 'aggregated database',
    'ANCIENT': 'ancient text',
    'ART': 'art work',
    'BILL': 'bill/resolution',
    'BLOG': 'blog',
    'BOOK': 'book',
    'CASE': 'case',
    'CHAP': 'book chapter',
    'CHART': 'chart',
    'CLSWK': 'classical cork',
    'COMP': 'computer program',
    'CONF': 'conference proceeding',
    'CPAPER': 'conference paper',
    'CTLG': 'catalog',
    'DATA': 'data file',
    'DBASE': 'online database',
    'DICT': 'dictionary',
    'EBOOK': 'electronic book',
    'ECHAP': 'electronic book chapter',
    'EDBOOK': 'edited book',
    'EJOUR': 'electronic article',
    'ELEC': 'web page',
    'ENCYC': 'encyclopedia',
    'EQUA': 'equation',
    'FIGURE': 'figure',
    'GEN': 'generic',
    'GOVDOC': 'government document',
    'GRANT': 'grant',
    'HEAR': 'hearing',
    'ICOMM': 'internet communication',
    'INPR': 'in press',
    'JFULL': 'journal (full)',
    'JOUR': 'journal',
    'LEGAL': 'legal rule or regulation',
    'MANSCPT': 'manuscript',
    'MAP': 'map',
    'MGZN': 'magazine article',
    'MPCT': 'motion picture',
    'MULTI': 'online multimedia',
    'MUSIC': 'music score',
    'NEWS': 'newspaper',
    'PAMP': 'pamphlet',
    'PAT': 'patent',
    'PCOMM': 'personal communication',
    'RPRT': 'report',
    'SER': 'serial publication',
    'SLIDE': 'slide',
    'SOUND': 'sound recording',
    'STAND': 'standard',
    'STAT': 'statute',
    'THES': 'thesis/dissertation',
    'UNBILL': 'unenacted bill/resolution',
    'UNPB': 'unpublished work',
    'VIDEO': 'video recording',
}

MULTI_TAGS = {'A1', 'A2', 'A3', 'A4', 'AD', 'AU', 'KW', 'N1'}
IGNORE_TAGS = {'FN', 'VR', 'EF'}
START_TAGS = {'TY', 'PT'}
END_TAG = 'ER'

TAGv1_RE = re.compile(r'^(?P<tag>[A-Z][A-Z0-9])(  - )')
TAGv2_RE = re.compile(r'^(?P<tag>[A-Z][A-Z0-9])( )|^(?P<endtag>E[FR])(\s?$)')

TAG_VALUE_SANITIZERS = {
    'DA': lambda x: parse_date(x).strftime('%Y-%m-%d'),
    'PY': lambda x: int(x),
    'TC': lambda x: int(x),
    'TY': lambda x: REFERENCE_TYPES_MAPPING.get(x, x),
    'Y1': lambda x: parse_date('-'.join(item if item else '01' for item in x[:-1].split('/'))),
    'Y2': lambda x: min(parse_date(val) for val in x.split(' through ')),
    }


class RisFile(object):
    """
    Args:
        path (str): RIS file to be parsed
        tag_key_map (dict): mapping of short RIS tags to human-readable keys
        tag_value_sanitizers (dict): mapping of short RIS tags to functions that
            sanitize their associated values
    """

    def __init__(self, path,
                 tag_key_map=None,
                 tag_value_sanitizers=None):
        self.path = path
        self.tag_key_map = (tag_key_map if tag_key_map
                                else tag_key_map)
        self.tag_value_sanitizers = (tag_value_sanitizers if tag_value_sanitizers
                                     else TAG_VALUE_SANITIZERS)
        self.in_record = False
        self.tag_re = None
        self.prev_line_len = None
        self.prev_tag = None
        self.record = {}

    def parse(self):
        """
        Yields:
            dict: next complete citation record

        Raises:
            IOError
        """
        with io.open(self.path, mode='rt') as f:
            for i, line in enumerate(f):

                # skip empty lines
                if not line.strip():
                    continue

                # automatically detect regex needed for this RIS file
                if self.tag_re is None:
                    if TAGv1_RE.match(line):
                        self.tag_re = TAGv1_RE
                    elif TAGv2_RE.match(line):
                        self.tag_re = TAGv2_RE
                    else:
                        msg ='tags in file {} not formatted as expected!'.format(self.path)
                        raise IOError(msg)

                tag_match = self.tag_re.match(line)
                # lines starts with a tag
                if tag_match:

                    tag = tag_match.group('tag') or tag_match.group('endtag')

                    if tag in IGNORE_TAGS:
                        self._stash_prev_info(tag, len(line))
                        continue

                    elif tag == END_TAG:
                        if self.in_record is False:
                            msg = 'found end tag, but not in a record!\nline: {} {}'.format(i, line.strip())
                            raise IOError(msg)

                        yield self.record  # record is complete! spit it out here

                        self.in_record = False
                        self.record = {}
                        self._stash_prev_info(tag, len(line))
                        continue

                    elif tag in START_TAGS:
                        if self.in_record is True:
                            msg = 'found start tag, but already in a record!\nline: {} {}'.format(i, line.strip())
                            raise IOError(msg)
                        self.in_record = True
                        self._add_tag_line(tag, line, tag_match.end())
                        self._stash_prev_info(tag, len(line))
                        continue

                    if self.in_record is False:
                        msg = 'start/end tag mismatch!\nline: {} {}'.format(i, line.strip())
                        raise IOError(msg)

                    if tag in self.tag_key_map:
                        self._add_tag_line(tag, line, tag_match.end())
                        self._stash_prev_info(tag, len(line))
                        continue

                    # multi-value tag line happens to start with a tag-compliant string
                    if self.prev_tag in MULTI_TAGS:
                        self._add_tag_line(self.prev_tag, line, 0)
                        continue

                    # no idea what this is, but might as well save it
                    print('unknown tag: tag={}, line={} "{}"'.format(tag, i, line.strip()))
                    self.record[tag] = line[tag_match.end():].strip()
                    self._stash_prev_info(tag, len(line))
                    continue

                # subsequent line belonging to a multi-value tag
                elif self.prev_tag in MULTI_TAGS:
                    self._add_tag_line(self.prev_tag, line, 0)
                    continue

                # single-value tag split across multiple lines, ugh
                elif line.startswith('   ') or self.prev_line_len > 70:
                    key = self.tag_key_map[self.prev_tag]
                    self.record[key] += ' ' + line.strip()

                else:
                    print('bad line: prev_tag={}, line={} "{}"'.format(
                        self.prev_tag, i, line.strip()))

    def _add_tag_line(self, tag, line, start_idx):
        """
        Args:
            tag (str)
            line (str)
            start_idx (int)
        """
        key = self.tag_key_map[tag]
        value = line[start_idx:].strip()
        # try to sanitize value, but don't sweat failure
        try:
            value = TAG_VALUE_SANITIZERS[tag](value)
        except KeyError:
            pass
        except Exception:
            print('value sanitization error: key={}, value={}'.format(key, value))
        # for multi-value tags, append to a list
        if tag in MULTI_TAGS:
            try:
                self.record[key].append(value)
            except KeyError:
                self.record[key] = [value]
        # otherwise, add key:value to record
        else:
            if key in self.record:
                print('duplicate key error: key={}, value={}'.format(key, value))
            self.record[key] = value

    def _stash_prev_info(self, tag, line_len):
        """
        Args:
            tag (str)
            line_len (int)
        """
        self.prev_tag = tag
        self.prev_line_len = line_len
