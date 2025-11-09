import apiflask as af
import marshmallow as ma

from ...lib import constants


# TODO: someday, we should rename this from "fields" to "include"
class FieldsSchema(af.Schema):
    fields_ = af.fields.DelimitedList(
        af.fields.String,
        required=False,
        delimiter=",",
        data_key="fields",
        description="comma-delimited list of entity fields to include in response",
    )

    @ma.post_load
    def add_id_if_not_specified(self, data: dict, **kwargs) -> dict:
        if data.get("fields_") and "id" not in data["fields_"]:
            data["fields_"].append("id")
        return data


class TokenSchema(af.Schema):
    access_token = af.fields.String(required=True)


class TokensSchema(af.Schema):
    access_token = af.fields.String(required=True)
    refresh_token = af.fields.String(required=True)


class UserSchema(af.Schema):
    id = af.fields.Integer(required=True, dump_only=True)
    name = af.fields.String(
        required=True, validate=af.validators.Length(min=1, max=200)
    )
    email = af.fields.String(
        required=True, validate=[af.validators.Email(), af.validators.Length(max=200)]
    )
    password = af.fields.String(
        required=True, load_only=True, validate=af.validators.Length(min=6, max=60)
    )
    is_confirmed = af.fields.Boolean()
    is_admin = af.fields.Boolean()
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")


class ReviewSchema(af.Schema):
    id = af.fields.Integer(required=True, dump_only=True)
    name = af.fields.String(required=True, validate=af.validators.Length(max=500))
    description = af.fields.String(load_default=None)
    status = af.fields.String(validate=af.validators.OneOf(constants.REVIEW_STATUSES))
    num_citation_screening_reviewers = af.fields.Integer(
        validate=af.validators.Range(min=1, max=3)
    )
    num_fulltext_screening_reviewers = af.fields.Integer(
        validate=af.validators.Range(min=1, max=3)
    )
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")


class ReviewerNumPct(af.Schema):
    num = af.fields.Integer(required=True, validate=af.validators.Range(min=1, max=3))
    pct = af.fields.Integer(required=True, validate=af.validators.Range(min=0, max=100))


class ReviewV2Schema(af.Schema):
    id = af.fields.Integer(required=True, dump_only=True)
    name = af.fields.String(required=True, validate=af.validators.Length(max=500))
    description = af.fields.String(load_default=None)
    status = af.fields.String(validate=af.validators.OneOf(constants.REVIEW_STATUSES))
    citation_reviewer_num_pcts = af.fields.List(af.fields.Nested(ReviewerNumPct))
    fulltext_reviewer_num_pcts = af.fields.List(af.fields.Nested(ReviewerNumPct))
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")


class ReviewPlanPICO(af.Schema):
    population = af.fields.String(validate=af.validators.Length(max=300))
    intervention = af.fields.String(validate=af.validators.Length(max=300))
    comparison = af.fields.String(validate=af.validators.Length(max=300))
    outcome = af.fields.String(validate=af.validators.Length(max=300))


class ReviewPlanKeyterm(af.Schema):
    group = af.fields.String(required=True, validate=af.validators.Length(max=100))
    term = af.fields.String(required=True, validate=af.validators.Length(max=100))
    synonyms = af.fields.List(
        af.fields.String(validate=af.validators.Length(max=100)), load_default=[]
    )


class ReviewPlanSelectionCriterion(af.Schema):
    label = af.fields.String(required=True, validate=af.validators.Length(max=50))
    description = af.fields.String(validate=af.validators.Length(max=300))


class DataExtractionFormItem(af.Schema):
    label = af.fields.String(required=True, validate=af.validators.Length(max=50))
    description = af.fields.String(validate=af.validators.Length(max=300))
    field_type = af.fields.String(
        required=True,
        validate=af.validators.OneOf(
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
    allowed_values = af.fields.List(af.fields.String())


class ReviewPlanSuggestedKeyterms(af.Schema):
    sample_size = af.fields.Integer(required=True, validate=af.validators.Range(min=1))
    incl_keyterms = af.fields.List(af.fields.String(), required=True)
    excl_keyterms = af.fields.List(af.fields.String(), required=True)


class ReviewPlanSchema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")
    objective = af.fields.String()
    research_questions = af.fields.List(
        af.fields.String(validate=af.validators.Length(max=300))
    )
    pico = af.fields.Nested(ReviewPlanPICO)
    keyterms = af.fields.Nested(ReviewPlanKeyterm, many=True)
    selection_criteria = af.fields.Nested(ReviewPlanSelectionCriterion, many=True)
    data_extraction_form = af.fields.Nested(DataExtractionFormItem, many=True)
    suggested_keyterms = af.fields.Nested(ReviewPlanSuggestedKeyterms)
    boolean_search_query = af.fields.String(dump_only=True)


class DataSourceSchema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    source_type = af.fields.String(
        required=True,
        validate=af.validators.OneOf(["database", "gray literature"]),
        description="type of source through which citation/s was/were found",
    )
    source_name = af.fields.String(
        load_default=None,
        validate=af.validators.Length(max=100),
        description="name of source through which citation/s was/were found",
    )
    source_url = af.fields.String(
        load_default=None,
        validate=[af.validators.URL(relative=False), af.validators.Length(max=500)],
        description="url of source through which citation/s was/were found",
    )
    source_type_and_name = af.fields.String(dump_only=True)


class ImportSchema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    review_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    user_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    data_source_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_BIGINT)
    )
    record_type = af.fields.String(
        required=True, validate=af.validators.OneOf(["citation", "fulltext"])
    )
    num_records = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    status = af.fields.String(validate=af.validators.OneOf(constants.IMPORT_STATUSES))
    data_source = af.fields.Nested(DataSourceSchema)
    user = af.fields.Nested(UserSchema)


class ScreeningSchema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")
    review_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    user_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    citation_id = af.fields.Integer(
        load_default=None, validate=af.validators.Range(min=1, max=constants.MAX_BIGINT)
    )
    fulltext_id = af.fields.Integer(
        load_default=None, validate=af.validators.Range(min=1, max=constants.MAX_BIGINT)
    )
    status = af.fields.String(
        required=True, validate=af.validators.OneOf(["included", "excluded"])
    )
    exclude_reasons = af.fields.List(
        af.fields.String(validate=af.validators.Length(max=64)), load_default=None
    )


class ScreeningV2Schema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")
    review_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    user_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    study_id = af.fields.Integer(
        load_default=None, validate=af.validators.Range(min=1, max=constants.MAX_BIGINT)
    )
    stage = af.fields.String(
        validate=af.validators.OneOf(["citation", "fulltext"])
    )  # TODO: required=True
    status = af.fields.String(
        required=True, validate=af.validators.OneOf(["included", "excluded"])
    )
    exclude_reasons = af.fields.List(
        af.fields.String(validate=af.validators.Length(max=64)), load_default=None
    )


class CitationSchema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")
    review_id = af.fields.Integer(
        required=True, validate=af.validators.Range(min=1, max=constants.MAX_INT)
    )
    type_of_work = af.fields.String(
        load_default=None, validate=af.validators.Length(max=25)
    )
    title = af.fields.String(validate=af.validators.Length(max=300))
    secondary_title = af.fields.String(
        load_default=None, validate=af.validators.Length(max=300)
    )
    abstract = af.fields.String(load_default=None)
    pub_year = af.fields.Integer(
        load_default=None,
        validate=af.validators.Range(min=1, max=constants.MAX_SMALLINT),
    )
    pub_month = af.fields.Integer(
        load_default=None,
        validate=af.validators.Range(min=1, max=constants.MAX_SMALLINT),
    )
    authors = af.fields.List(af.fields.String(validate=af.validators.Length(max=100)))
    keywords = af.fields.List(af.fields.String(validate=af.validators.Length(max=100)))
    type_of_reference = af.fields.String(
        load_default=None, validate=af.validators.Length(max=50)
    )
    journal_name = af.fields.String(
        load_default=None, validate=af.validators.Length(max=100)
    )
    volume = af.fields.String(load_default=None, validate=af.validators.Length(max=20))
    issue_number = af.fields.String(
        load_default=None, validate=af.validators.Length(max=20)
    )
    doi = af.fields.String(load_default=None, validate=af.validators.Length(max=100))
    issn = af.fields.String(load_default=None, validate=af.validators.Length(max=20))
    publisher = af.fields.String(
        load_default=None, validate=af.validators.Length(max=100)
    )
    language = af.fields.String(
        load_default=None, validate=af.validators.Length(max=50)
    )
    other_fields = af.fields.Dict()
    screenings = af.fields.Nested(ScreeningSchema, many=True, dump_only=True)


class FulltextSchema(af.Schema):
    id = af.fields.Integer(dump_only=True)
    review_id = af.fields.Integer(required=True, validate=af.validators.Range(min=1))
    filename = af.fields.String(validate=af.validators.Length(max=30))
    original_filename = af.fields.String(dump_only=True)
    text_content = af.fields.String(dump_only=True)
    screenings = af.fields.Nested(ScreeningSchema, many=True, dump_only=True)
    created_at = af.fields.DateTime(dump_only=True, format="iso")
    updated_at = af.fields.DateTime(dump_only=True, format="iso")
