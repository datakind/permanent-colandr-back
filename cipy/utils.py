from __future__ import absolute_import, division, print_function, unicode_literals

import itertools
import re


def present_citation(citation):
    print('\nTITLE:    {}'.format(citation.get('title')))
    print('YEAR:     {}'.format(citation.get('publication_year')))
    print('AUTHORS:  {}'.format('; '.join(citation.get('authors', []))))
    print('ABSTRACT: {}'.format(citation.get('abstract')))
    print('DOI:      {}'.format(citation.get('doi')))


def get_boolean_search_query(keyterms):
    return '\nAND\n'.join(_boolify_group_terms(group_terms)
                          for _, group_terms
                          in itertools.groupby(keyterms, key=lambda x: x['group']))


def _boolify_term_set(term_set):
    if term_set.get('synonyms'):
        return '(' + ' OR '.join('"{}"'.format(term)
                                 for term in [term_set['term']] + term_set['synonyms']) + ')'
    else:
        return '"{}"'.format(term_set['term'])


def _boolify_group_terms(group_terms):
    group_terms = list(group_terms)
    if len(group_terms) > 1:
        return '(' + ' OR '.join(_boolify_term_set(term_set)
                                 for term_set in group_terms) + ')'
    else:
        return ' OR '.join(_boolify_term_set(term_set)
                           for term_set in group_terms)


def get_keyterms_regex(keyterms):
    all_terms = [re.escape(term)
                 for term_set in keyterms
                 for term in [term_set['term']] + term_set.get('synonyms')]
    keyterms_re = re.compile(r'(?<=^|\b)(' + '|'.join(all_terms) + r')(?=$|\b)',
                             flags=re.IGNORECASE | re.UNICODE)
    return keyterms_re
