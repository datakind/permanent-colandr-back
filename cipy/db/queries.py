
GET_CANDIDATE_DUPE_CLUSTERS = """
SELECT
    t1.citation_id, t1.authors, t1.title, t1.abstract, t1.publication_year, t1.doi,
    t2.block_id, t2.smaller_ids
FROM
    citations AS t1,
    dedupe_smaller_coverage AS t2
WHERE
    t1.review_id = %(review_id)s
    AND t1.citation_id = t2.citation_id
ORDER BY t2.block_id
"""

# TODO: add review_id filter to these queries?
DUPLICATE_CITATION_IDS = """
    ((SELECT citation_id FROM duplicates)
     EXCEPT (SELECT canonical_citation_id FROM duplicates))
"""

SELECT_CITATIONS_TO_SCREEN = """
SELECT
    t1.citation_id,
    TRIM('\n' FROM concat_ws('\n\n', COALESCE(title, ''),
                             COALESCE(abstract, ''),
                             COALESCE(array_to_string(keywords, ', '), ''))
        ) AS citation_text
FROM
    citations AS t1,
    citation_status AS t2,
    reviews AS t3
WHERE
    t1.review_id = %(review_id)s
    AND t3.review_id = %(review_id)s
    AND t1.citation_id = t2.citation_id
    AND t2.status != 'excluded'
    AND CAST(t2.deduplication->>'is_duplicate' AS boolean) IS FALSE
    AND (t2.citation_screening IS NULL
         OR jsonb_array_length(t2.citation_screening) < CAST(t3.settings->>'num_citation_screenign_reviewers' AS INT))
ORDER BY random()
LIMIT %(sample_size)s
"""
