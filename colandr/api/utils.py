import itertools
from collections.abc import Iterable, Sequence
from operator import itemgetter


def assign_status(screening_statuses: Sequence[str], num_screeners: int) -> str:
    """
    Assign a status to a citation or fulltext, depending on the status decisions
    of all existing screenings and the number of required screeners.

    Args:
        screening_statuses
        num_screeners

    Returns:
        'not_screened', 'screened_once', 'screened_twice', 'included', or 'excluded'
    """
    num_screenings = len(screening_statuses)
    if num_screenings == 0:
        return "not_screened"
    elif num_screenings < num_screeners:
        if num_screenings == 1:
            return "screened_once"
        else:
            return "screened_twice"
    else:
        if all(status == "excluded" for status in screening_statuses):
            return "excluded"
        elif all(status == "included" for status in screening_statuses):
            return "included"
        else:
            return "conflict"


def get_boolean_search_query(keyterms: Iterable[dict]) -> str:
    """
    Build a boolean search query from the ``keyterms`` in a review plan.

    Args:
        keyterms
    """
    return "\nAND\n".join(
        _boolify_group_terms(group_terms)
        for _, group_terms in itertools.groupby(keyterms, key=itemgetter("group"))
    )


def _boolify_term_set(term_set: dict) -> str:
    if term_set.get("synonyms"):
        return (
            "("
            + " OR ".join(
                '"{}"'.format(term)
                for term in [term_set["term"]] + term_set["synonyms"]
            )
            + ")"
        )
    else:
        return '"{}"'.format(term_set["term"])


def _boolify_group_terms(group_terms: Iterable[dict]) -> str:
    group_terms = list(group_terms)
    if len(group_terms) > 1:
        return (
            "("
            + " OR ".join(_boolify_term_set(term_set) for term_set in group_terms)
            + ")"
        )
    else:
        return " OR ".join(_boolify_term_set(term_set) for term_set in group_terms)
