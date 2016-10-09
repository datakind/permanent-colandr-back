import re


def get_keyterms_regex(keyterms):
    """
    Args:
        keyterms (List[dict])

    Returns:
        :class:``_sre.SRE_Pattern``,: ``re.compile`` object
    """
    all_terms = [re.escape(term)
                 for term_set in keyterms
                 for term in [term_set['term']] + term_set.get('synonyms')]
    keyterms_re = re.compile(r'(?<=^|\b)(' + '|'.join(all_terms) + r')(?=$|\b)',
                             flags=re.IGNORECASE | re.UNICODE)
    return keyterms_re
