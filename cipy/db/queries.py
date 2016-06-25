
GET_CITATIONS_FOR_DEDUPE_TRAINING = """
    SELECT citation_id, authors, title, abstract, publication_year, doi
    FROM citations
    """


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


GET_SAMPLE_FOR_DUPE_THRESHOLD = """
    SELECT citation_id, authors, title, abstract, publication_year, doi
    FROM citations
    WHERE project_id = %(project_id)s
    ORDER BY random()
    LIMIT 10000
    """


GET_DUPE_CLUSTER_CANONICAL_ID = """
    SELECT
        citation_id,
        ((CASE WHEN authors IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN title IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN abstract IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN publication_year IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN doi IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN type_of_work IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN publication_month IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN keywords IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN journal_name IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN type_of_reference IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN volume IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN issue_number IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN issn IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN publisher IS NULL THEN 1 ELSE 0 END)
        + (CASE WHEN language IS NULL THEN 1 ELSE 0 END)) AS n_null_cols
    FROM citations
    WHERE
        project_id = %(project_id)s
        AND citation_id IN %(citation_ids)s
    ORDER BY n_null_cols ASC
    LIMIT 1
    """
