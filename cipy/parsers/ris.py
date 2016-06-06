from __future__ import absolute_import, division, print_function, unicode_literals

import io
import logging
import re

from dateutil.parser import parse as parse_date


LOGGER = logging.getLogger(__name__)

KEY_MAP = {
    'A1': 'primary_authors',  # special: Lastname, Firstname, Suffix
    'A2': 'secondary_authors',  # special: Lastname, Firstname, Suffix
    'A3': 'tertiary_authors',  # special: Lastname, Firstname, Suffix
    'A4': 'subsidiary_authors',  # special: Lastname, Firstname, Suffix
    'AB': 'abstract',
    'AD': 'author_addresses',
    'AN': 'accession_number',
    'AR': 'article_number',
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
    'CL': 'conference_location',
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
    'EI': 'electronic_intl_issn',
    'EM': 'email_address',
    'EP': 'end_page',
    'ER': 'end_of_reference',  # special: must be empty and last tag of record
    'ET': 'edition',
    'FN': 'file_name',  # ignore!
    'FU': 'funding_agency_and_grants',
    'FX': 'funding_text',
    'GA': 'document_delivery_number',
    'HO': 'conference_host',
    'ID': 'reference_id',
    'IS': 'issue_number',
    'J1': 'journal_name_user_abbr_1',
    'J2': 'journal_name_user_abbr_2',
    'J9': 'source_abbr_29char',
    'JA': 'journal_name_abbr',
    'JF': 'journal_name',
    'JI': 'source_abbr_iso',
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
    'NR': 'num_cited_references',
    'NV': 'number_of_volumes',
    'OI': 'open_researcher_contributor_id',
    'OP': 'original_publication',
    'PA': 'publisher_address',
    'PB': 'publisher',
    'PD': 'publication_month',  # HACK: should actually be "publication_date"
    'PG': 'page_count',
    'PI': 'publisher_city',
    'PM': 'pubmed_id',
    'PN': 'part_number',
    'PP': 'publishing_place',
    'PT': 'publication_type',
    'PY': 'publication_year',  # special: YYYY
    'PU': 'publisher',
    'RI': 'reviewed_item',
    'RN': 'research_notes',
    'RP': 'reprint_status',  # special: 'IN FILE', 'NOT IN FILE', or 'ON REQUEST (MM/DD/YY)'
    'SC': 'subject_categories',
    'SE': 'section',
    'SI': 'special_issue',
    'SN': 'issn',
    'SO': 'source_name',
    'SP': 'pages',
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
    'WC': 'subject_categories_alt',
    'Y1': 'primary_date',  # special: YYYY/
    'Y2': 'access_date',
    'Z9': 'num_times_cited',
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

JOURNAL_TAGS = ('JF', 'JO', 'JA', 'JI', 'J1', 'J2', 'J9')
AUTHOR_TAGS = ('AU', 'A1', 'A2', 'A3', 'A4', 'TA')

TAGv1_RE = re.compile(r'^(?P<tag>[A-Z][A-Z0-9])(  - )')
TAGv2_RE = re.compile(r'^(?P<tag>[A-Z][A-Z0-9])( )|^(?P<endtag>E[FR])(\s?$)')

_MONTH_MAP = {'spr': 3, 'sum': 6, 'fal': 9, 'win': 12,
              'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
              'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12}

def _sanitize_pd_tag(value):
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

VALUE_SANITIZERS = {
    'DA': lambda x: parse_date(x).strftime('%Y-%m-%d'),
    'PD': _sanitize_pd_tag,
    'PM': int,
    'PY': int,
    'TC': int,
    'TY': lambda x: REFERENCE_TYPES_MAPPING.get(x, x),
    'Y1': lambda x: parse_date('-'.join(item if item else '01' for item in x[:-1].split('/'))),
    'Y2': lambda x: min(parse_date(val) for val in x.split(' through ')),
    }


class RisFile(object):
    """
    Args:
        path (str): RIS file to be parsed
        key_map (dict or bool): mapping of short RIS tags to to human-readable keys;
            if None (default), default mapping is used; if False, no mapping will be done
        value_sanitizers (dict or bool): mapping of short RIS tags to functions
            that sanitize their associated values; if None (default), default
            sanitizers will be used; if False, no sanitization will be performed
    """

    def __init__(self, path,
                 key_map=None,
                 value_sanitizers=None):
        self.path = path
        self.key_map = (key_map if key_map is not None
                        else KEY_MAP)
        self.value_sanitizers = (value_sanitizers if value_sanitizers is not None
                                 else VALUE_SANITIZERS)
        if self.key_map:
            self.multi_keys = {self.key_map.get(tag, tag) for tag in MULTI_TAGS}
            self.split_keys = {self.key_map.get(tag, tag) for tag in ('SC', 'WC')}
            self.journal_keys = tuple(self.key_map.get(tag, tag) for tag in JOURNAL_TAGS)
            self.author_keys = tuple(self.key_map.get(tag, tag) for tag in AUTHOR_TAGS)
        else:
            self.multi_keys = MULTI_TAGS
            self.split_keys = {'SC', 'WC'}
            self.journal_keys = JOURNAL_TAGS
            self.author_keys = AUTHOR_TAGS
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

                # get rid of byte order mark (BOM)
                if i == 0 and line.startswith('\ufeff'):
                    line = line[1:]

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
                        msg ='tags in file {}, lineno {}, line {} not formatted as expected!'.format(self.path, i, line)
                        LOGGER.error(msg)
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
                            LOGGER.error(msg)
                            raise IOError(msg)

                        self._sort_multi_values()
                        self._sanitize_record()
                        yield self.record  # record is complete! spit it out here

                        self.in_record = False
                        self.record = {}
                        self._stash_prev_info(tag, len(line))
                        continue

                    elif tag in START_TAGS:
                        if self.in_record is True:
                            msg = 'found start tag, but already in a record!\nline: {} {}'.format(i, line.strip())
                            LOGGER.error(msg)
                            raise IOError(msg)
                        self.in_record = True
                        self._add_tag_line(tag, line, tag_match.end())
                        self._stash_prev_info(tag, len(line))
                        continue

                    if self.in_record is False:
                        msg = 'start/end tag mismatch!\nline: {} {}'.format(i, line.strip())
                        LOGGER.error(msg)
                        raise IOError(msg)

                    if self.key_map and tag in self.key_map:
                        self._add_tag_line(tag, line, tag_match.end())
                        self._stash_prev_info(tag, len(line))
                        continue

                    # multi-value tag line happens to start with a tag-compliant string
                    if self.prev_tag in MULTI_TAGS:
                        self._add_tag_line(self.prev_tag, line, 0)
                        continue

                    # no idea what this is, but might as well save it
                    LOGGER.debug('unknown tag: tag=%s, line=%s "%s"', tag, i, line.strip())
                    self.record[tag] = line[tag_match.end():].strip()
                    self._stash_prev_info(tag, len(line))
                    continue

                # subsequent line belonging to a multi-value tag
                elif self.prev_tag in MULTI_TAGS:
                    self._add_tag_line(self.prev_tag, line, 0)
                    continue

                # single-value tag split across multiple lines, ugh
                elif line.startswith('   ') or self.prev_line_len > 70:
                    key = (self.key_map.get(self.prev_tag, self.prev_tag) if self.key_map
                           else self.prev_tag)
                    self.record[key] += ' ' + line.strip()

                else:
                    LOGGER.error('bad line: prev_tag=%s, line=%s "%s"',
                        self.prev_tag, i, line.strip())

    def _add_tag_line(self, tag, line, start_idx):
        """
        Args:
            tag (str)
            line (str)
            start_idx (int)
        """
        key = (self.key_map[tag] if self.key_map
               else tag)
        value = line[start_idx:].strip()
        # try to sanitize value, but don't sweat failure
        try:
            value = self.value_sanitizers[tag](value)
        except KeyError:
            pass
        except Exception:
            LOGGER.exception('value sanitization error: key=%s, value=%s',
                key, value)
        # for multi-value tags, append to a list
        if tag in MULTI_TAGS:
            try:
                self.record[key].append(value)
            except KeyError:
                self.record[key] = [value]
        # otherwise, add key:value to record
        else:
            if key in self.record:
                LOGGER.error('duplicate key error: key=%s, value=%s', key, value)
            self.record[key] = value

    def _stash_prev_info(self, tag, line_len):
        """
        Args:
            tag (str)
            line_len (int)
        """
        self.prev_tag = tag
        self.prev_line_len = line_len

    def _sort_multi_values(self):
        for key in self.multi_keys:
            try:
                self.record[key] = tuple(sorted(self.record[key]))
            except KeyError:
                pass
            except Exception:
                LOGGER.exception('multi-value sort error: key=%s, value=%s',
                    key, self.record[key])

    def _sanitize_record(self):
        for key in self.split_keys:
            try:
                self.record[key] = tuple(sorted(self.record[key].split('; ')))
            except KeyError:
                pass
            except Exception:
                LOGGER.exception('record sanitization error: key=%s, value=%s',
                    key, self.record[key])
        if not self.record.get('journal_name'):
            for key in self.journal_keys:
                try:
                    self.record['journal_name'] = self.record[key]
                    break
                except KeyError:
                    continue
        if not self.record.get('authors'):
            for key in self.author_keys:
                try:
                    self.record['authors'] = self.record[key]
                    break
                except KeyError:
                    continue
