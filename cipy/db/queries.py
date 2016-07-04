
GET_CANDIDATE_DUPE_CLUSTERS = """
    SELECT
        t1.citation_id, t1.authors, t1.title, t1.abstract, t1.publication_year, t1.doi,
        t2.block_id, t2.smaller_ids
    FROM
        citations AS t1,
        dedupe_smaller_coverage AS t2
    WHERE
        project_id = %(project_id)s
        AND t1.citation_id = t2.citation_id
        AND t1.citation_id NOT IN (SELECT citation_id
                                   FROM duplicates
                                   WHERE project_id = %(project_id)s)
    ORDER BY t2.block_id
"""

DUPLICATE_CITATION_IDS = """
    ((SELECT citation_id FROM duplicates)
     EXCEPT (SELECT canonical_citation_id FROM duplicates))
"""

GET_CITATION_TEXTS_SAMPLE = """
    SELECT
        citation_id,
        TRIM('\n' FROM CONCAT_WS('\n\n', COALESCE(title, ''),
                       COALESCE(abstract, ''),
                       COALESCE(ARRAY_TO_STRING(keywords, ', '), ''))) AS citation_text
    FROM citations
    WHERE
        project_id = %(project_id)s
        AND citation_id NOT IN {duplicate_citation_ids}
    ORDER BY random()
    LIMIT 1000
""".format(duplicate_citation_ids=DUPLICATE_CITATION_IDS)
