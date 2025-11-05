import apiflask as af
import marshmallow as ma


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
