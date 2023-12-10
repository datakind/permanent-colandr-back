import arrow
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask_restx import Namespace, Resource
from marshmallow import fields as ma_fields
from marshmallow.validate import Range
from webargs.fields import DelimitedList
from webargs.flaskparser import use_args, use_kwargs

from ...extensions import db
from ...lib import constants, sanitizers
from ...models import DataExtraction, ReviewPlan, Study
from ..errors import bad_request_error, forbidden_error, not_found_error
from ..schemas import DataExtractionSchema, ExtractedItem
from ..swagger import extracted_item_model


ns = Namespace(
    "data_extractions",
    path="/data_extractions",
    description="get, delete, and modify data extractions",
)


@ns.route("/<int:id>")
@ns.doc(
    summary="get, delete, and modify data extractions",
    produces=["application/json"],
)
class DataExtractionResource(Resource):
    @ns.doc(
        responses={
            200: "successfully got data extraction record",
            403: "current app user forbidden to get data extraction record",
            404: "no data extraction with matching id was found",
        }
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @jwtext.jwt_required()
    def get(self, id):
        """get data extraction record for a single study by id"""
        current_user = jwtext.get_current_user()
        # check current user authorization
        extracted_data = db.session.get(DataExtraction, id)
        if not extracted_data:
            return not_found_error(f"<DataExtraction(study_id={id})> not found")
        if (
            current_user.is_admin is False
            and current_user.reviews.filter_by(
                id=extracted_data.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to get extracted data for this study"
            )
        current_app.logger.debug("got %s", extracted_data)
        return DataExtractionSchema().dump(extracted_data)

    @ns.doc(
        description='Since data extractions are automatically created upon fulltext inclusion and deleted upon fulltext exclusion, "delete" here amounts to nulling out some or all of its non-required fields',
        params={
            "labels": {
                "in": "query",
                "type": "string",
                "description": 'comma-delimited list-as-string of data extraction labels to "delete" (set to null)',
            },
        },
        responses={
            204: "successfully deleted (nulled) data extraction record",
            403: "current app user forbidden to delete data extraction record",
            404: "no data extraction with matching id was found",
        },
    )
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @use_kwargs(
        {
            "labels": DelimitedList(ma_fields.String, delimiter=",", load_default=None),
        },
        location="query",
    )
    @jwtext.jwt_required(fresh=True)
    def delete(self, id, labels):
        """delete data extraction record for a single study by id"""
        current_user = jwtext.get_current_user()
        # check current user authorization
        extracted_data = db.session.get(DataExtraction, id)
        if not extracted_data:
            return not_found_error(f"<DataExtraction(study_id={id})> not found")
        if (
            current_user.user_review_assoc.filter_by(
                review_id=extracted_data.review_id
            ).one_or_none()
            is None
        ):
            return forbidden_error(
                f"{current_user} forbidden to get extracted data for this study"
            )
        if labels:
            extracted_data.extracted_items = [
                item
                for item in extracted_data.extracted_items
                if item["label"] not in labels
            ]
        else:
            extracted_data.extracted_items = []
        # in case of "full" deletion, update study's data_extraction_status
        if not extracted_data.extracted_items:
            study = db.session.get(Study, id)
            study.data_extraction_status = "not_started"
        db.session.commit()
        current_app.logger.info("deleted contents of %s", extracted_data)
        return "", 204

    @ns.doc(
        expect=([extracted_item_model], "data extraction data to be modified"),
        responses={
            200: "data extraction data was modified",
            403: "current app user forbidden to modify data extraction",
            404: "no data extraction with matching id was found",
        },
    )
    @use_args(ExtractedItem(many=True), location="json")
    @use_kwargs(
        {
            "id": ma_fields.Int(
                required=True, validate=Range(min=1, max=constants.MAX_BIGINT)
            ),
        },
        location="view_args",
    )
    @jwtext.jwt_required()
    def put(self, args, id):
        """modify data extraction record for a single study by id"""
        current_user = jwtext.get_current_user()
        # check current user authorization
        extracted_data = db.session.get(DataExtraction, id)
        review_id = extracted_data.review_id
        if not extracted_data:
            return not_found_error(f"<DataExtraction(study_id={id})> not found")
        if (
            current_user.user_review_assoc.filter_by(review_id=review_id).one_or_none()
            is None
        ):
            return forbidden_error(
                "{} forbidden to modify extracted data for this study".format(
                    current_user
                )
            )
        study = db.session.get(Study, id)
        if study.data_extraction_status == "finished":
            return forbidden_error(
                f'{extracted_data} already "finished", so can\'t be modified'
            )
        data_extraction_form = db.session.execute(
            sa.select(ReviewPlan.data_extraction_form).filter_by(id=review_id)
        ).scalar_one_or_none()
        if not data_extraction_form:
            return forbidden_error(
                f"<ReviewPlan({review_id})> does not have a data extraction form"
            )
        labels_map = {
            item["label"]: (item["field_type"], set(item.get("allowed_values", [])))
            for item in data_extraction_form[0]
        }
        # manually validate inputs, given data extraction form specification
        if isinstance(extracted_data.extracted_items, dict):
            extracted_data.extracted_items = []
        extracted_data_map = {
            item["label"]: item["value"] for item in extracted_data.extracted_items
        }
        for item in args:
            label = item["label"]
            value = item["value"]
            if label not in labels_map:
                return bad_request_error(
                    f"label '{label}' invalid; available choices are {list(labels_map.keys())}"
                )
            field_type, allowed_values = labels_map[label]
            if field_type == "bool":
                if value in (1, True, "true", "t"):
                    validated_value = True
                elif value in (0, False, "false", "f"):
                    validated_value = False
                else:
                    return bad_request_error(
                        f'value "{value}" for label "{label}" invalid; must be {field_type}'
                    )
            elif field_type == "date":
                try:
                    validated_value = str(arrow.get(value).naive)
                except arrow.parser.ParserError:
                    return bad_request_error(
                        f'value "{value}" for label "{label}" invalid; must be ISO-formatted {field_type}'
                    )
            elif field_type in ("int", "float", "str"):
                type_ = (
                    int
                    if field_type == "int"
                    else float
                    if field_type == "float"
                    else str
                )
                validated_value = sanitizers.sanitize_type(value, type_)
                if validated_value is None:
                    return bad_request_error(
                        'value "{}" for label "{}" invalid; must be {}'.format(
                            value, label, field_type
                        )
                    )
            elif field_type == "select_one":
                if value not in allowed_values:
                    return bad_request_error(
                        f'value "{value}" for label "{label}" invalid; must be one of {allowed_values}'
                    )
                validated_value = value
            elif field_type == "select_many":
                validated_value = []
                for val in value:
                    if val not in allowed_values:
                        return bad_request_error(
                            f'value "{val}" for label "{label}" invalid; must be one of {allowed_values}'
                        )
                    validated_value.append(val)
            # TODO: implement this country validation
            elif field_type == "country":
                return bad_request_error(
                    '"country" validation has not yet been implemented -- sorry!'
                )
            else:
                return bad_request_error(f'field_type "{field_type}" is not valid')
            extracted_data_map[label] = validated_value
        extracted_data.extracted_items = [
            {"label": label, "value": value}
            for label, value in extracted_data_map.items()
        ]
        # also update study's data_extraction_status
        study.data_extraction_status = "started"

        db.session.commit()
        current_app.logger.info("modified %s", extracted_data)
        return DataExtractionSchema().dump(extracted_data)
