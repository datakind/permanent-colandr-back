import apiflask as af


# TODO: someday, we should rename this from"fields" to "include"
class FieldsInput(af.Schema):
    fields_ = af.fields.DelimitedList(
        af.fields.String, delimiter=",", load_default="", data_key="fields"
    )


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
