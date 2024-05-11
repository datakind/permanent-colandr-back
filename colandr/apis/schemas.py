from marshmallow import Schema, fields
from marshmallow.validate import URL, Email, Length, OneOf, Range

from ..lib import constants


class UserSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    name = fields.Str(required=True, validate=Length(min=1, max=200))
    email = fields.Str(required=True, validate=[Email(), Length(max=200)])
    password = fields.Str(load_only=True, required=True, validate=Length(min=6, max=60))
    is_confirmed = fields.Boolean()
    is_admin = fields.Boolean()


class DataSourceSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    source_type = fields.Str(
        required=True, validate=OneOf(["database", "gray literature"])
    )
    source_name = fields.Str(load_default=None, validate=Length(max=100))
    source_url = fields.Str(
        load_default=None, validate=[URL(relative=False), Length(max=500)]
    )
    source_type_and_name = fields.Str(dump_only=True)


class ReviewerNumPct(Schema):
    num = fields.Int(required=True, validate=Range(min=1, max=3))
    pct = fields.Int(required=True, validate=Range(min=0, max=100))


class ReviewSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    name = fields.Str(required=True, validate=Length(max=500))
    description = fields.Str(load_default=None)
    status = fields.Str(validate=OneOf(constants.REVIEW_STATUSES))
    num_citation_screening_reviewers = fields.Int(validate=Range(min=1, max=3))
    num_fulltext_screening_reviewers = fields.Int(validate=Range(min=1, max=3))


class ReviewV2Schema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    name = fields.Str(required=True, validate=Length(max=500))
    description = fields.Str(load_default=None)
    status = fields.Str(validate=OneOf(constants.REVIEW_STATUSES))
    citation_reviewer_num_pcts = fields.List(fields.Nested(ReviewerNumPct))
    fulltext_reviewer_num_pcts = fields.List(fields.Nested(ReviewerNumPct))


class ReviewPlanPICO(Schema):
    population = fields.Str(validate=Length(max=300))
    intervention = fields.Str(validate=Length(max=300))
    comparison = fields.Str(validate=Length(max=300))
    outcome = fields.Str(validate=Length(max=300))


class ReviewPlanKeyterm(Schema):
    group = fields.Str(required=True, validate=Length(max=100))
    term = fields.Str(required=True, validate=Length(max=100))
    synonyms = fields.List(fields.Str(validate=Length(max=100)), load_default=[])


class ReviewPlanSelectionCriterion(Schema):
    label = fields.Str(required=True, validate=Length(max=50))
    description = fields.Str(validate=Length(max=300))


class DataExtractionFormItem(Schema):
    label = fields.Str(required=True, validate=Length(max=50))
    description = fields.Str(validate=Length(max=300))
    field_type = fields.Str(
        required=True,
        validate=OneOf(
            [
                "bool",
                "date",
                "int",
                "float",
                "str",
                "select_one",
                "select_many",
                "country",
            ]
        ),
    )
    allowed_values = fields.List(fields.Str())


class ReviewPlanSuggestedKeyterms(Schema):
    sample_size = fields.Int(required=True, validate=Range(min=1))
    incl_keyterms = fields.List(fields.Str(), required=True)
    excl_keyterms = fields.List(fields.Str(), required=True)


class ReviewPlanSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    objective = fields.Str()
    research_questions = fields.List(fields.Str(validate=Length(max=300)))
    pico = fields.Nested(ReviewPlanPICO)
    keyterms = fields.Nested(ReviewPlanKeyterm, many=True)
    selection_criteria = fields.Nested(ReviewPlanSelectionCriterion, many=True)
    data_extraction_form = fields.Nested(DataExtractionFormItem, many=True)
    suggested_keyterms = fields.Nested(ReviewPlanSuggestedKeyterms)
    boolean_search_query = fields.Str(dump_only=True)


class ImportSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    user_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    data_source_id = fields.Int(
        required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
    )
    record_type = fields.Str(required=True, validate=OneOf(["citation", "fulltext"]))
    num_records = fields.Int(
        required=True, validate=Range(min=1, max=constants.MAX_INT)
    )
    status = fields.Str(validate=OneOf(constants.IMPORT_STATUSES))
    data_source = fields.Nested(DataSourceSchema)
    user = fields.Nested(UserSchema)


class DedupeSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    study_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    duplicate_of = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_BIGINT)
    )
    # TODO: figure out if allow_nan parameter is required here
    # https://marshmallow.readthedocs.io/en/stable/upgrading.html#float-field-takes-a-new-allow-nan-parameter
    duplicate_score = fields.Float(load_default=None, validate=Range(min=0.0, max=1.0))


class ScreeningSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    user_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    citation_id = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_BIGINT)
    )
    fulltext_id = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_BIGINT)
    )
    status = fields.Str(required=True, validate=OneOf(["included", "excluded"]))
    exclude_reasons = fields.List(
        fields.Str(validate=Length(max=64)), load_default=None
    )


class ScreeningV2Schema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    user_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    study_id = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_BIGINT)
    )
    stage = fields.Str(validate=OneOf(["citation", "fulltext"]))  # TODO: required=True
    status = fields.Str(required=True, validate=OneOf(["included", "excluded"]))
    exclude_reasons = fields.List(
        fields.Str(validate=Length(max=64)), load_default=None
    )


class CitationSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    type_of_work = fields.Str(load_default=None, validate=Length(max=25))
    title = fields.Str(validate=Length(max=300))
    secondary_title = fields.Str(load_default=None, validate=Length(max=300))
    abstract = fields.Str(load_default=None)
    pub_year = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_SMALLINT)
    )
    pub_month = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_SMALLINT)
    )
    authors = fields.List(fields.Str(validate=Length(max=100)))
    keywords = fields.List(fields.Str(validate=Length(max=100)))
    type_of_reference = fields.Str(load_default=None, validate=Length(max=50))
    journal_name = fields.Str(load_default=None, validate=Length(max=100))
    volume = fields.Str(load_default=None, validate=Length(max=20))
    issue_number = fields.Str(load_default=None, validate=Length(max=20))
    doi = fields.Str(load_default=None, validate=Length(max=100))
    issn = fields.Str(load_default=None, validate=Length(max=20))
    publisher = fields.Str(load_default=None, validate=Length(max=100))
    language = fields.Str(load_default=None, validate=Length(max=50))
    other_fields = fields.Dict()
    screenings = fields.Nested(ScreeningSchema, many=True, dump_only=True)


class FulltextSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    filename = fields.Str(validate=Length(max=30))
    original_filename = fields.Str(dump_only=True)
    text_content = fields.Str(dump_only=True)
    screenings = fields.Nested(ScreeningSchema, many=True, dump_only=True)


class ExtractedItem(Schema):
    label = fields.Str(required=True, validate=Length(max=50))
    # validation handled in API Resource based on values in DataExtractionFormItem
    value = fields.Raw(required=True)


class DataExtractionSchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    study_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    extracted_items = fields.Nested(ExtractedItem, many=True)


class StudyCitationSchema(Schema):
    type_of_work = fields.Str(load_default=None, validate=Length(max=25))
    title = fields.Str(validate=Length(max=300))
    secondary_title = fields.Str(load_default=None, validate=Length(max=300))
    abstract = fields.Str(load_default=None)
    pub_year = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_SMALLINT)
    )
    pub_month = fields.Int(
        load_default=None, validate=Range(min=1, max=constants.MAX_SMALLINT)
    )
    authors = fields.List(fields.Str(validate=Length(max=100)))
    keywords = fields.List(fields.Str(validate=Length(max=100)))
    type_of_reference = fields.Str(load_default=None, validate=Length(max=50))
    journal_name = fields.Str(load_default=None, validate=Length(max=100))
    volume = fields.Str(load_default=None, validate=Length(max=20))
    issue_number = fields.Str(load_default=None, validate=Length(max=20))
    doi = fields.Str(load_default=None, validate=Length(max=100))
    issn = fields.Str(load_default=None, validate=Length(max=20))
    publisher = fields.Str(load_default=None, validate=Length(max=100))
    language = fields.Str(load_default=None, validate=Length(max=50))
    other_fields = fields.Dict()


class StudyFulltextSchema(Schema):
    filename = fields.Str(validate=Length(max=30))
    original_filename = fields.Str(dump_only=True)
    text_content = fields.Str(dump_only=True)


class StudySchema(Schema):
    id = fields.Int(dump_only=True)
    created_at = fields.DateTime(dump_only=True, format="iso")
    updated_at = fields.DateTime(dump_only=True, format="iso")
    citation = fields.Nested(StudyCitationSchema, dump_only=True)
    fulltext = fields.Nested(StudyFulltextSchema, dump_only=True)
    user_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    review_id = fields.Int(required=True, validate=Range(min=1, max=constants.MAX_INT))
    data_source_id = fields.Int(
        required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
    )
    tags = fields.List(fields.Str(validate=Length(max=64)))
    dedupe = fields.Nested(DedupeSchema, dump_only=True)
    dedupe_status = fields.Str(
        dump_only=True, validate=OneOf(constants.DEDUPE_STATUSES)
    )
    citation = fields.Nested(CitationSchema, dump_only=True)
    citation_status = fields.Str(
        dump_only=True, validate=OneOf(constants.SCREENING_STATUSES)
    )
    fulltext = fields.Nested(FulltextSchema, dump_only=True)
    fulltext_status = fields.Str(
        dump_only=True, validate=OneOf(constants.SCREENING_STATUSES)
    )
    data_extraction = fields.Nested(DataExtractionSchema, dump_only=True)
    data_extraction_status = fields.Str(validate=OneOf(constants.EXTRACTION_STATUSES))
