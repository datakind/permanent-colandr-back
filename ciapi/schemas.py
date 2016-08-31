from marshmallow import Schema, fields
from marshmallow.validate import Email, Length, Range


class UserSchema(Schema):
    user_id = fields.Int(
        dump_only=True, validate=Range(min=1, max=2147483647))
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    name = fields.Str(
        required=True, validate=Length(min=1, max=200))
    email = fields.Email(
        required=True, validate=[Email(), Length(max=200)])
    password = fields.Str(
        required=True, load_only=True)
    review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        missing=None)
    owned_review_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        missing=None)

    class Meta:
        strict = True


class ReviewSettingsSchema(Schema):
    num_citation_screening_reviewers = fields.Int(
        required=True, missing=2, validate=Range(min=1, max=3))
    num_fulltext_screening_reviewers = fields.Int(
        required=True, missing=2, validate=Range(min=1, max=3))
    required_citation_screener_id = fields.Int(
        missing=None, validate=Range(min=0, max=2147483647))
    required_fulltext_screener_id = fields.Int(
        missing=None, validate=Range(min=0, max=2147483647))

    class Meta:
        strict = True


class ReviewSchema(Schema):
    review_id = fields.Int(
        dump_only=True)
    created_at = fields.DateTime(
        dump_only=True, format='iso')
    owner_user_id = fields.Int(
        required=True, missing=0, validate=Range(min=1, max=2147483647))
    user_ids = fields.List(
        fields.Int(validate=Range(min=1, max=2147483647)),
        required=True, missing=[])
    name = fields.Str(
        required=True, validate=Length(max=500))
    description = fields.Str(
        missing=None)
    settings = fields.Nested(
        ReviewSettingsSchema,
        required=True, missing=ReviewSettingsSchema().load({}).data)

    class Meta:
        strict = True


# TODO
class ReviewPlan(Schema):

    class Meta:
        strict = True


# TODO
class Citation(Schema):

    class Meta:
        strict = True


# TODO
class CitationStatus(Schema):

    class Meta:
        strict = True
