import itertools
from operator import itemgetter


def assign_status(screening_statuses, num_screeners):
    """
    Assign a status to a citation or fulltext, depending on the status decisions
    of all existing screenings and the number of required screeners.

    Args:
        screening_statuses (List[str] or Tuple[str])
        num_screeners (int)

    Returns:
        str: one of 'not_screened', 'screened_once', 'screened_twice',
            'included', or 'excluded'
    """
    num_screenings = len(screening_statuses)
    if num_screenings == 0:
        return 'not_screened'
    elif num_screenings < num_screeners:
        if num_screenings == 1:
            return 'screened_once'
        else:
            return 'screened_twice'
    else:
        if all(status == 'excluded' for status in screening_statuses):
            return 'excluded'
        elif all(status == 'included' for status in screening_statuses):
            return 'included'
        else:
            return 'conflict'


def get_boolean_search_query(keyterms):
    """
    Build a boolean search query from the ``keyterms`` in a review plan.

    Args:
        keyterms (List[dict])

    Returns
        str
    """
    return '\nAND\n'.join(_boolify_group_terms(group_terms)
                          for _, group_terms
                          in itertools.groupby(keyterms, key=itemgetter('group')))


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
