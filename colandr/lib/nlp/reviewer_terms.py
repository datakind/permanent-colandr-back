import logging
import math
import re


def get_keyterms_regex(keyterms):
    """
    Args:
        keyterms (List[dict]): given by :attr:``ReviewPlan.keyterms``

    Returns:
        :class:``_sre.SRE_Pattern``: compiled regex object for all terms
    """
    all_terms = [
        re.escape(term)
        for term_set in keyterms
        for term in [term_set["term"]] + term_set.get("synonyms", [])
    ]
    keyterms_re = re.compile(
        r"(?<=^|\b)(" + "|".join(all_terms) + r")(?=$|\b)",
        flags=re.IGNORECASE | re.UNICODE,
    )
    return keyterms_re


def get_incl_excl_terms_regex(suggested_keyterms):
    """
    Args:
        suggested_keyterms (dict): given by :attr:``ReviewPlan.suggested_keyterms``

    Returns:
        :class:``_sre.SRE_Pattern``: compiled regex pattern for included terms
        :class:``_sre.SRE_Pattern``: compiled regex pattern for excluded terms
    """
    incl_keyterms = suggested_keyterms.get("incl_keyterms", [])
    excl_keyterms = suggested_keyterms.get("excl_keyterms", [])
    incl_regex = re.compile(
        r"(?<=^|\b)(" + "|".join(incl_keyterms) + r")(?=$|\b)",
        flags=re.IGNORECASE | re.UNICODE,
    )
    excl_regex = re.compile(
        r"(?<=^|\b)(" + "|".join(excl_keyterms) + r")(?=$|\b)",
        flags=re.IGNORECASE | re.UNICODE,
    )
    return incl_regex, excl_regex


def get_keyterms_score(keyterms_regex, text_content):
    """
    Args:
        keyterms_regex (:class:``_sre.SRE_Pattern``)
        text_content (str): given by :attr:``Citation.text_content``

    Returns:
        float: higher values => more relevant
    """
    full_len = len(text_content)
    if full_len == 0:
        return 0.0
    match_len = sum(
        len(match.group()) for match in keyterms_regex.finditer(text_content)
    )
    nonmatch_len = full_len - match_len
    try:
        return math.sqrt(full_len) * match_len / nonmatch_len
    except ValueError:
        logging.exception("error: %s, %s, %s", match_len, nonmatch_len, full_len)
        return 0.0


def get_incl_excl_terms_score(incl_regex, excl_regex, text_content):
    """
    Args:
        incl_regex (:class:``_sre.SRE_Pattern``)
        excl_regex (:class:``_sre.SRE_Pattern``)
        text_content (str): given by :attr:``Citation.text_content``

    Returns:
        float: higher values => more relevant
    """
    if len(text_content) == 0:
        return 0.0
    n_incl_matches = 1 + sum(1 for _ in incl_regex.finditer(text_content))
    n_excl_matches = 1 + sum(1 for _ in excl_regex.finditer(text_content))
    return math.log(n_incl_matches / n_excl_matches)
