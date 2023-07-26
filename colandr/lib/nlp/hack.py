from __future__ import annotations

import math
from decimal import Decimal
from operator import itemgetter
from typing import Iterable

import numpy as np
from textacy import representations


def most_discriminating_terms(
    terms_lists: Iterable[Iterable[str]],
    bool_array_grp1: Iterable[bool],
    *,
    max_n_terms: int = 1000,
    top_n_terms: int | float = 25,
) -> tuple[list[str], list[str]]:
    """
    Given a collection of documents assigned to 1 of 2 exclusive groups, get the
    ``top_n_terms`` most discriminating terms for group1-and-not-group2 and
    group2-and-not-group1.

    Args:
        terms_lists: Sequence of documents, each as a sequence of (str) terms;
            used as input to :func:`doc_term_matrix()`
        bool_array_grp1: Ordered sequence of True/False values,
            where True corresponds to documents falling into "group 1" and False
            corresponds to those in "group 2".
        max_n_terms: Only consider terms whose document frequency is within
            the top ``max_n_terms`` out of all distinct terms; must be > 0.
        top_n_terms: If int (must be > 0), the total number of most discriminating terms
            to return for each group; if float (must be in the interval (0, 1)),
            the fraction of ``max_n_terms`` to return for each group.

    Returns:
        List of the top ``top_n_terms`` most discriminating terms for grp1-not-grp2, and
        list of the top ``top_n_terms`` most discriminating terms for grp2-not-grp1.

    References:
        King, Gary, Patrick Lam, and Margaret Roberts. "Computer-Assisted Keyword
        and Document Set Discovery from Unstructured Text." (2014).
        http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.458.1445&rep=rep1&type=pdf
    """
    alpha_grp1 = 1
    alpha_grp2 = 1
    if isinstance(top_n_terms, float):
        top_n_terms = int(round(top_n_terms * max_n_terms))
    bool_array_grp1 = np.array(bool_array_grp1)
    bool_array_grp2 = np.invert(bool_array_grp1)

    vectorizer = representations.Vectorizer(
        tf_type="linear",
        norm=None,
        idf_type="smooth",
        min_df=3,
        max_df=0.95,
        max_n_terms=max_n_terms,
    )
    dtm = vectorizer.fit_transform(terms_lists)
    id2term = vectorizer.id_to_term

    # get doc freqs for all terms in grp1 documents
    dtm_grp1 = dtm[bool_array_grp1, :]
    n_docs_grp1 = dtm_grp1.shape[0]
    doc_freqs_grp1 = representations.get_doc_freqs(dtm_grp1)

    # get doc freqs for all terms in grp2 documents
    dtm_grp2 = dtm[bool_array_grp2, :]
    n_docs_grp2 = dtm_grp2.shape[0]
    doc_freqs_grp2 = representations.get_doc_freqs(dtm_grp2)

    # get terms that occur in a larger fraction of grp1 docs than grp2 docs
    term_ids_grp1 = np.where(
        doc_freqs_grp1 / n_docs_grp1 > doc_freqs_grp2 / n_docs_grp2
    )[0]

    # get terms that occur in a larger fraction of grp2 docs than grp1 docs
    term_ids_grp2 = np.where(
        doc_freqs_grp1 / n_docs_grp1 < doc_freqs_grp2 / n_docs_grp2
    )[0]

    # get grp1 terms doc freqs in and not-in grp1 and grp2 docs, plus marginal totals
    grp1_terms_grp1_df = doc_freqs_grp1[term_ids_grp1]
    grp1_terms_grp2_df = doc_freqs_grp2[term_ids_grp1]
    # grp1_terms_grp1_not_df = n_docs_grp1 - grp1_terms_grp1_df
    # grp1_terms_grp2_not_df = n_docs_grp2 - grp1_terms_grp2_df
    # grp1_terms_total_df = grp1_terms_grp1_df + grp1_terms_grp2_df
    # grp1_terms_total_not_df = grp1_terms_grp1_not_df + grp1_terms_grp2_not_df

    # get grp2 terms doc freqs in and not-in grp2 and grp1 docs, plus marginal totals
    grp2_terms_grp2_df = doc_freqs_grp2[term_ids_grp2]
    grp2_terms_grp1_df = doc_freqs_grp1[term_ids_grp2]
    # grp2_terms_grp2_not_df = n_docs_grp2 - grp2_terms_grp2_df
    # grp2_terms_grp1_not_df = n_docs_grp1 - grp2_terms_grp1_df
    # grp2_terms_total_df = grp2_terms_grp2_df + grp2_terms_grp1_df
    # grp2_terms_total_not_df = grp2_terms_grp2_not_df + grp2_terms_grp1_not_df

    # get grp1 terms likelihoods, then sort for most discriminating grp1-not-grp2 terms
    grp1_terms_likelihoods = {}
    for idx, term_id in enumerate(term_ids_grp1):
        term1 = (
            Decimal(math.factorial(grp1_terms_grp1_df[idx] + alpha_grp1 - 1))
            * Decimal(math.factorial(grp1_terms_grp2_df[idx] + alpha_grp2 - 1))
            / Decimal(
                math.factorial(
                    grp1_terms_grp1_df[idx]
                    + grp1_terms_grp2_df[idx]
                    + alpha_grp1
                    + alpha_grp2
                    - 1
                )
            )
        )
        term2 = (
            Decimal(
                math.factorial(n_docs_grp1 - grp1_terms_grp1_df[idx] + alpha_grp1 - 1)
            )
            * Decimal(
                math.factorial(n_docs_grp2 - grp1_terms_grp2_df[idx] + alpha_grp2 - 1)
            )
            / Decimal(
                (
                    math.factorial(
                        n_docs_grp1
                        + n_docs_grp2
                        - grp1_terms_grp1_df[idx]
                        - grp1_terms_grp2_df[idx]
                        + alpha_grp1
                        + alpha_grp2
                        - 1
                    )
                )
            )
        )
        grp1_terms_likelihoods[id2term[term_id]] = term1 * term2
    top_grp1_terms = [
        term
        for term, likelihood in sorted(
            grp1_terms_likelihoods.items(), key=itemgetter(1), reverse=True
        )[:top_n_terms]
    ]

    # get grp2 terms likelihoods, then sort for most discriminating grp2-not-grp1 terms
    grp2_terms_likelihoods = {}
    for idx, term_id in enumerate(term_ids_grp2):
        term1 = (
            Decimal(math.factorial(grp2_terms_grp2_df[idx] + alpha_grp2 - 1))
            * Decimal(math.factorial(grp2_terms_grp1_df[idx] + alpha_grp1 - 1))
            / Decimal(
                math.factorial(
                    grp2_terms_grp2_df[idx]
                    + grp2_terms_grp1_df[idx]
                    + alpha_grp2
                    + alpha_grp1
                    - 1
                )
            )
        )
        term2 = (
            Decimal(
                math.factorial(n_docs_grp2 - grp2_terms_grp2_df[idx] + alpha_grp2 - 1)
            )
            * Decimal(
                math.factorial(n_docs_grp1 - grp2_terms_grp1_df[idx] + alpha_grp1 - 1)
            )
            / Decimal(
                (
                    math.factorial(
                        n_docs_grp2
                        + n_docs_grp1
                        - grp2_terms_grp2_df[idx]
                        - grp2_terms_grp1_df[idx]
                        + alpha_grp2
                        + alpha_grp1
                        - 1
                    )
                )
            )
        )
        grp2_terms_likelihoods[id2term[term_id]] = term1 * term2
    top_grp2_terms = [
        term
        for term, likelihood in sorted(
            grp2_terms_likelihoods.items(), key=itemgetter(1), reverse=True
        )[:top_n_terms]
    ]

    return (top_grp1_terms, top_grp2_terms)
