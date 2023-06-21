# maximum values for SQL SmallInt, Int, and BigInt column types
MAX_SMALLINT = 32767
MAX_INT = 2147483647
MAX_BIGINT = 9223372036854775807

DEDUPE_FIELDS = [
    {"field": "authors", "type": "Set", "has missing": True},
    {"field": "title", "type": "String", "has missing": True},
    {"field": "abstract", "type": "Text", "has missing": True},
    {
        "field": "pub_year",
        "type": "Exact",
        "has missing": True,
    },  # NOTE: used to be publication_year
    {"field": "doi", "type": "String", "has missing": True},
]

CITATION_RANKING_MODEL_FNAME = "citation_ranking_model_review_{review_id}.pkl"

IMPORT_STATUSES = ("not_screened", "included", "excluded")
REVIEW_STATUSES = ("active", "frozen")
DEDUPE_STATUSES = ("not_duplicate", "duplicate")
SCREENING_STATUSES = (
    "not_screened",
    "screened_once",
    "conflict",
    "included",
    "excluded",
)
USER_SCREENING_STATUSES = (
    "pending",
    "awaiting_coscreener",
    "conflict",
    "included",
    "excluded",
)
EXTRACTION_STATUSES = ("not_started", "started", "finished")
