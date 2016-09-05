import json

from marshmallow import Schema, fields, post_dump
from marshmallow.validate import Email, Length, OneOf, Range

MAX_SMALLINT = 32767
MAX_INT = 2147483647
MAX_BIGINT = 9223372036854775807


class UserSchema(Schema):
    id = fields.Int(
        dump_only=True, validate=Range(min=1, max=MAX_INT))
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    name = fields.Str(
        required=True, validate=Length(min=1, max=200))
    email = fields.Email(
        required=True, validate=[Email(), Length(max=200)])
    password = fields.Str(
        load_only=True, required=True, validate=Length(min=6, max=60))

    class Meta:
        strict = True


class ReviewSettingsSchema(Schema):
    num_citation_screening_reviewers = fields.Int(
        required=True, missing=2, validate=Range(min=1, max=3))
    num_fulltext_screening_reviewers = fields.Int(
        required=True, missing=2, validate=Range(min=1, max=3))

    class Meta:
        strict = True


class ReviewSchema(Schema):
    id = fields.Int(
        dump_only=True)
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    name = fields.Str(
        required=True, validate=Length(max=500))
    description = fields.Str(
        missing=None)
    status = fields.Str(
        validate=OneOf(['active', 'archived']))
    settings = fields.Nested(
        ReviewSettingsSchema,
        required=True, missing=ReviewSettingsSchema().load({}).data)
    owner_user_id = fields.Int(
        required=True, validate=Range(min=1, max=MAX_INT))

    class Meta:
        strict = True


class ReviewPlanResearchQuestion(Schema):
    question = fields.Str(
        required=True, validate=Length(max=300))
    rank = fields.Int(
        required=True, validate=Range(min=1))

    class Meta:
        strict = True


class ReviewPlanPICO(Schema):
    population = fields.Str(
        validate=Length(max=300))
    intervention = fields.Str(
        validate=Length(max=300))
    comparison = fields.Str(
        validate=Length(max=300))
    outcome = fields.Str(
        validate=Length(max=300))

    class Meta:
        strict = True


class ReviewPlanKeyterm(Schema):
    group = fields.Str(
        required=True, validate=Length(max=100))
    term = fields.Str(
        required=True, validate=Length(max=100))
    synonyms = fields.List(
        fields.Str(validate=Length(max=100)),
        missing=[])

    class Meta:
        strict = True


class ReviewPlanSelectionCriterion(Schema):
    label = fields.Str(
        required=True, validate=Length(max=25))
    description = fields.Str(
        validate=Length(max=300))

    class Meta:
        strict = True


# TODO
class ReviewPlanDataExtractionForm(Schema):
    class Meta:
        strict = True


class ReviewPlan(Schema):
    id = fields.Int(
        dump_only=True)
    review_id = fields.Int(
        required=True, validate=Range(min=1, max=MAX_INT))
    objective = fields.Str()
    research_questions = fields.Nested(
        ReviewPlanResearchQuestion, many=True,
        missing=[])
    pico = fields.Nested(
        ReviewPlanPICO,
        missing={})
    keyterms = fields.Nested(
        ReviewPlanKeyterm, many=True,
        missing=[])
    selection_criteria = fields.Nested(
        ReviewPlanSelectionCriterion, many=True,
        required=True, missing=[])
    data_extraction_form = fields.Nested(
        ReviewPlanDataExtractionForm,
        required=True, missing=[])

    class Meta:
        strict = True


class StudyDeduplication(Schema):
    is_duplicate = fields.Bool(
        required=True)
    is_duplicate_of = fields.Int(
        validate=Range(min=1, max=MAX_BIGINT))
    duplicate_score = fields.Float(
        validate=Range(min=0.0, max=1.0))
    user_id = fields.Int(
        missing=None, validate=Range(min=1, max=MAX_INT))

    class Meta:
        strict = True


class StudyScreening(Schema):
    status = fields.Str(
        validate=OneOf(['included', 'excluded']))
    exclude_reasons = fields.List(
        fields.Str(validate=Length(max=25)), missing=None)
    user_id = fields.Int(
        missing=None, validate=Range(min=1, max=MAX_INT))

    class Meta:
        strict = True


class Study(Schema):
    id = fields.Int(
        dump_only=True)
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    review_id = fields.Int(
        required=True, validate=Range(min=1, max=MAX_INT))
    title = fields.Str(
        validate=Length(max=250))
    tags = fields.List(
        fields.Str(validate=Length(max=25)))
    status = fields.Str(
        validate=OneOf(['included', 'excluded', 'pending', 'conflict']))
    deduplication = fields.Nested(
        StudyDeduplication)
    citation_screening = fields.Nested(
        StudyScreening, many=True)
    fulltext_screening = fields.Nested(
        StudyScreening, many=True)

    class Meta:
        strict = True


class Citation(Schema):
    id = fields.Int(
        dump_only=True)
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    study_id = fields.Int(
        required=True, validate=Range(min=1, max=MAX_BIGINT))
    type_of_work = fields.Str(
        validate=Length(max=25))
    title = fields.Str(
        validate=Length(max=250))
    secondary_title = fields.Str(
        validate=Length(max=250))
    abstract = fields.Str()
    pub_year = fields.Int(
        validate=Range(min=1, max=MAX_SMALLINT))
    pub_month = fields.Int(
        validate=Range(min=1, max=MAX_SMALLINT))
    authors = fields.List(
        fields.Str(validate=Length(max=100)))
    keywords = fields.List(
        fields.Str(validate=Length(max=100)))
    type_of_reference = fields.Str(
        validate=Length(max=50))
    journal_name = fields.Str(
        validate=Length(max=100))
    volume = fields.Str(
        validate=Length(max=20))
    issue_number = fields.Str(
        validate=Length(max=20))
    doi = fields.Str(
        validate=Length(max=100))
    issn = fields.Str(
        validate=Length(max=20))
    publisher = fields.Str(
        validate=Length(max=50))
    language = fields.Str(
        validate=Length(max=50))
    other_fields = fields.Dict()

    # @post_dump
    # def json_to_string(self, data):
    #     if data.get('other_fields'):
    #         data['other_fields'] = json.dumps(data['other_fields'])
    #     return data

    class Meta:
        strict = True


class Fulltext(Schema):
    id = fields.Int(
        dump_only=True)
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    study_id = fields.Int(
        required=True, validate=Range(min=1, max=MAX_BIGINT))
    filename = fields.Str()
    content = fields.Str()
    extracted_info = fields.Dict()

    class Meta:
        strict = True
