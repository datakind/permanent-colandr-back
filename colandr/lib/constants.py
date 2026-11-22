import enum


# maximum values for SQL SmallInt, Int, and BigInt column types
MAX_SMALLINT = 32767
MAX_INT = 2147483647
MAX_BIGINT = 9223372036854775807

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


# enums used in db columns -- the *values* (not member names) are what's stored
# which is enforced by db constraints


class UserRoleDB(enum.StrEnum):
    OWNER = "owner"
    MEMBER = "member"


class ScreeningStageDB(enum.StrEnum):
    CITATION = "citation"
    FULLTEXT = "fulltext"


class ScreeningDecisionDB(enum.StrEnum):
    INCLUDED = "included"
    EXCLUDED = "excluded"
