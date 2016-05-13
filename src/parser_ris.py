"""
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
    'J1': 'journal_name_user_abbr',
    'J2': 'alternate_title',
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
    'RP': 'reprint_edition',  # special: 'IN FILE', 'NOT IN FILE', or 'ON REQUEST (MM/DD/YY)'
    'SE': 'section',
    'SN': 'issn',
    'SO': 'source_name',
    'SP': 'start_page',
    'ST': 'short_title',
    'T1': 'primary_title',
    'T2': 'secondary_title',  # note: journal_title, if applicable
    'T3': 'tertiary_title',
    'TA': 'translated_author',
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

REPEATABLE_TAGS = {'A1', 'A2', 'A3', 'A4', 'AD', 'AU', 'KW', 'N1'}
IGNORE_TAGS = {'FN', 'VR', 'EF'}
START_TAGS = {'TY', 'PT'}
END_TAG = 'ER'

TAG_RE = re.compile('^([A-Z][A-Z0-9])(  - | )|^(E[FR])($|  - | )')

VALUE_SANITIZERS = {
    'DA': lambda x: parse_date(x).strftime('%Y-%m-%d'),
    'EP': lambda x: int(x),
    'PY': lambda x: int(x),
    'SP': lambda x: int(x),
    'TY': lambda x: REFERENCE_TYPES_MAPPING.get(x, x),
    'Y1': lambda x: parse_date('-'.join(item if item else '01' for item in x[:-1].split('/'))),
    'Y2': lambda x: parse_date('-'.join(item if item else '01' for item in x[:-1].split('/')))
    }


def _add_tag(tag, line, match_end, record):
    key = TAG_KEY_MAPPING[tag]
    value = line[match_end:].strip()
    # try to sanitize value, but don't sweat failure
    try:
        value = VALUE_SANITIZERS[tag](value)
    except KeyError:
        pass
    except Exception:
        print('value sanitization error: key={}, value={}'.format(key, value))
    if tag in REPEATABLE_TAGS:
        try:
            record[key].append(value)
        except KeyError:
            record[key] = [value]
    else:
        if key in record:
            print('warning: key {} already included in record'.format(key))
        else:
            record[key] = value


def _add_repeatable_tag_line(tag, line, record):
    key = TAG_KEY_MAPPING[tag]
    try:
        record[key].append(line.strip())
    except KeyError:
        record[key] = [line.strip()]


def parse_ris_file(fname):
    with io.open(fname, mode='r') as f:

        in_record = False
        curr_tag = None
        record = {}
        records = []

        for i, line in enumerate(f):

            if not line.strip():
                continue

            tag_match = TAG_RE.match(line)
            if tag_match:
                tag = tag_match.group(1)

                if tag in IGNORE_TAGS:
                    continue

                elif tag == END_TAG:
                    if in_record is False:
                        msg = 'end tag on line {}, but already out of a record?!'.format(i)
                        raise Exception(msg)
                    records.append(record)
                    record = {}
                    curr_tag = tag
                    in_record = False
                    continue

                elif tag in START_TAGS:
                    if in_record is True:
                        msg = 'start tag on line {}, but already in a record?!'.format(i)
                        raise Exception(msg)
                    curr_tag = tag
                    in_record = True
                    _add_tag(tag, line, tag_match.end(), record)
                    continue

                if in_record is False:
                    raise Exception('there has been a start/end tag mismatch?!')

                if tag in TAG_KEY_MAPPING:
                    curr_tag = tag
                    _add_tag(tag, line, tag_match.end(), record)
                elif curr_tag == 'N1':  # unfortunate reference formatting
                    _add_repeatable_tag_line(curr_tag, line, record)
                else:
                    print('unknown tag:', line)

            elif curr_tag == 'AB':  # multi-line abstract
                key = TAG_KEY_MAPPING[curr_tag]
                record[key] += ' ' + line.strip()

            elif curr_tag in REPEATABLE_TAGS:
                _add_repeatable_tag_line(curr_tag, line, record)
            else:
                print('bad line: lineno={}, curr_tag={}, line={}'.format(i, curr_tag, line))

    return records
