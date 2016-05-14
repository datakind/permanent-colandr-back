"""
Parse .RIS files from Scopus or Mendeley, as well as plaintext exports from
Web of Science; return as a list of dictionaries, where each citation record
is a dictionary whose keys are field names and values are field values.
"""
import io
import re

from dateutil.parser import parse as parse_date


TAG_KEY_MAPPING = {
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

VALUE_SANITIZERS = {
    'DA': lambda x: parse_date(x).strftime('%Y-%m-%d'),
    'PY': lambda x: int(x),
    'TC': lambda x: int(x),
    'TY': lambda x: REFERENCE_TYPES_MAPPING.get(x, x),
    'Y1': lambda x: parse_date('-'.join(item if item else '01' for item in x[:-1].split('/'))),
    'Y2': lambda x: min(parse_date(val) for val in x.split(' through ')),
    }


def _add_tag_line(tag, line, start_idx, record):
    """
    Args:
        tag (str)
        line (str)
        start_idx (int)
        record (dict)
    """
    key = TAG_KEY_MAPPING[tag]
    value = line[start_idx:].strip()
    # try to sanitize value, but don't sweat failure
    try:
        value = VALUE_SANITIZERS[tag](value)
    except KeyError:
        pass
    except Exception:
        print('value sanitization error: key={}, value={}'.format(key, value))
    # for multi-value tags, append to a list
    if tag in MULTI_TAGS:
        try:
            record[key].append(value)
        except KeyError:
            record[key] = [value]
    # otherwise, add key:value to record
    else:
        if key in record:
            print('duplicate key error: key={}, value={}'.format(key, value))
        record[key] = value


def parse_file(path):
    """
    Args:
        path (str)
    """
    with io.open(path, mode='r') as f:

        in_record = False
        tag_re = None
        prev_tag = None
        record = {}
        records = []

        for i, line in enumerate(f):

            if not line.strip():
                continue

            # automatically detect regex needed for this RIS file
            if tag_re is None:
                tag_re = (TAGv1_RE if TAGv1_RE.match(line)
                          else TAGv2_RE if TAGv2_RE.match(line)
                          else None)
                if tag_re is None:
                    raise IOError('file {} is not formatted as expected!'.format(path))

            tag_match = tag_re.match(line)
            if tag_match:

                tag = tag_match.group('tag') or tag_match.group('endtag')

                if tag in IGNORE_TAGS:
                    prev_tag = tag
                    continue

                elif tag == END_TAG:
                    if in_record is False:
                        msg = 'found end tag, but not in a record!\nline: {} {}'.format(i, line.strip())
                        raise IOError(msg)
                    records.append(record)
                    in_record = False
                    record = {}
                    prev_tag = tag
                    continue

                elif tag in START_TAGS:
                    if in_record is True:
                        msg = 'found start tag, but already in a record!\nline: {} {}'.format(i, line.strip())
                        raise IOError(msg)
                    in_record = True
                    _add_tag_line(tag, line, tag_match.end(), record)
                    prev_tag = tag
                    continue

                if in_record is False:
                    raise IOError('start/end tag mismatch!\nline: {} {}'.format(i, line.strip()))

                if tag in TAG_KEY_MAPPING:
                    _add_tag_line(tag, line, tag_match.end(), record)
                    prev_tag = tag
                    continue

                # multi-value tag line happens to start with a tag-compliant string
                if prev_tag in MULTI_TAGS:
                    _add_tag_line(prev_tag, line, 0, record)
                    continue

                # no idea what this is, but might as well save it
                print('unknown tag: tag={}, line={} "{}"'.format(tag, i, line.strip()))
                record[tag] = line[tag_match.end():].strip()

            elif prev_tag in MULTI_TAGS:
                _add_tag_line(prev_tag, line, 0, record)
                continue

            # single-value tag split across multiple lines, ugh
            elif line.startswith('   '):
                key = TAG_KEY_MAPPING[prev_tag]
                record[key] += ' ' + line.strip()

            else:
                print('bad line: prev_tag={}, line={} "{}"'.format(prev_tag, i, line.strip()))

    return records
