from flask_restx import Namespace, fields

from ..lib import constants


ns = Namespace("models")


login_model = ns.model(
    "Login",
    {
        "email": fields.String(required=True),
        "password": fields.String(required=True),
    },
)

user_model = ns.model(
    "User",
    {
        "name": fields.String(required=True),
        "email": fields.String(required=True),
        "password": fields.String(required=True),
    },
)

data_source_model = ns.model(
    "DataSource",
    {
        "source_type": fields.String(
            required=True, enum=["database", "gray literature"]
        ),
        "source_name": fields.String(max_length=100),
        "source_url": fields.String(max_length=500),
    },
)

reviewer_num_pct_model = ns.model(
    "ReviewerNumPct",
    {"num": fields.Integer(min=1, max=3), "pct": fields.Integer(min=0, max=100)},
)

review_model = ns.model(
    "Review",
    {
        "name": fields.String(required=True, max_length=500),
        "description": fields.String,
        "status": fields.String,
        "num_citation_screening_reviewers": fields.Integer(min=1, max=3),
        "num_fulltext_screening_reviewers": fields.Integer(min=1, max=3),
    },
)

review_v2_model = ns.model(
    "ReviewV2",
    {
        "name": fields.String(required=True, max_length=500),
        "description": fields.String,
        "status": fields.String,
        "citation_reviewer_num_pcts": fields.List(
            fields.Nested(reviewer_num_pct_model)
        ),
        "fulltext_reviewer_num_pcts": fields.List(
            fields.Nested(reviewer_num_pct_model)
        ),
    },
)

review_plan_pico_model = ns.model(
    "ReviewPlanPico",
    {
        "population": fields.String(max_length=300),
        "intervention": fields.String(max_length=300),
        "comparison": fields.String(max_length=300),
        "outcome": fields.String(max_length=300),
    },
)

review_plan_keyterm_model = ns.model(
    "ReviewPlanKeyterm",
    {
        "group": fields.String(required=True, max_length=100),
        "term": fields.String(required=True, max_length=100),
        "synonyms": fields.List(fields.String(max_length=100)),
    },
)

review_plan_selection_criterion_model = ns.model(
    "ReviewPlanSelectionCriterion",
    {
        "label": fields.String(required=True, max_length=25),
        "description": fields.String(max_length=300),
    },
)

data_extraction_form_item_model = ns.model(
    "DataExtractionFormItem",
    {
        "label": fields.String(required=True, max_length=25),
        "description": fields.String(max_length=300),
        "field_type": fields.String(
            required=True,
            enum=[
                "bool",
                "date",
                "int",
                "float",
                "str",
                "select_one",
                "select_many",
                "country",
            ],
        ),
        "allowed_values": fields.List(fields.String),
    },
)

review_plan_suggested_keyterms = ns.model(
    "ReviewPlanSuggestedKeyterms",
    {
        "sample_size": fields.Integer(required=True, min=1),
        "incl_keyterms": fields.List(fields.String, required=True),
        "excl_keyterms": fields.List(fields.String, required=True),
    },
)

review_plan_model = ns.model(
    "ReviewPlan",
    {
        "objective": fields.String,
        "research_questions": fields.List(fields.String(max_length=300)),
        "pico": fields.Nested(review_plan_pico_model),
        "keyterms": fields.List(fields.Nested(review_plan_keyterm_model)),
        "selection_criteria": fields.List(
            fields.Nested(review_plan_selection_criterion_model)
        ),
        "data_extraction_form": fields.List(
            fields.Nested(data_extraction_form_item_model)
        ),
    },
    # 'suggested_keyterms': fields.Nested(review_plan_suggested_keyterms)}  # not user-set
)

import_model = ns.model(
    "Import",
    {
        "review_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "user_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "data_source_id": fields.Integer(
            required=True, min=1, max=constants.MAX_BIGINT
        ),
        "record_type": fields.String(required=True, enum=["citation", "fulltext"]),
        "num_records": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "status": fields.String(enum=constants.IMPORT_STATUSES),
    },
)

dedupe_model = ns.model(
    "Dedupe",
    {
        "review_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "duplicate_of": fields.Integer(min=1, max=constants.MAX_BIGINT),
        "duplicate_score": fields.Float(min=0.0, max=1.0),
    },
)

screening_model = ns.model(
    "Screening",
    {
        "review_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "user_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "citation_id": fields.Integer(min=1, max=constants.MAX_BIGINT),
        "fulltext_id": fields.Integer(min=1, max=constants.MAX_BIGINT),
        "status": fields.String(required=True, enum=["included", "excluded"]),
        "exclude_reasons": fields.List(fields.String(max_length=25)),
    },
)

citation_model = ns.model(
    "Citation",
    {
        "review_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "type_of_work": fields.String(max_length=25),
        "title": fields.String(max_length=300),
        "secondary_title": fields.String(max_length=300),
        "abstract": fields.String,
        "pub_year": fields.Integer(min=1, max=constants.MAX_SMALLINT),
        "pub_month": fields.Integer(min=1, max=constants.MAX_SMALLINT),
        "authors": fields.List(fields.String(max_length=100)),
        "keywords": fields.List(fields.String(max_length=100)),
        "type_of_reference": fields.String(max_length=50),
        "journal_name": fields.String(max_length=100),
        "volume": fields.String(max_length=20),
        "issue_number": fields.String(max_length=20),
        "doi": fields.String(max_length=100),
        "issn": fields.String(max_length=20),
        "publisher": fields.String(max_length=100),
        "language": fields.String(max_length=50),
        "other_fields": fields.Raw,
    },
)

fulltext_model = ns.model(
    "Fulltext",
    {"review_id": fields.Integer(required=True, min=1, max=constants.MAX_INT)},
)

extracted_item_model = ns.model(
    "ExtractedItem",
    {
        "label": fields.String(required=True, max_length=25),
        "value": fields.Raw(required=True),
    },
)

data_extraction_model = ns.model(
    "DataExtraction",
    {
        "review_id": fields.Integer(required=True, min=1, max=constants.MAX_INT),
        "extracted_items": fields.List(fields.Nested(extracted_item_model)),
    },
)

study_model = ns.model(
    "Study",
    {
        "data_extraction_status": fields.String(enum=constants.EXTRACTION_STATUSES),
        "tags": fields.List(fields.String(max_length=25)),
    },
)
