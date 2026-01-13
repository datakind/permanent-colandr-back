import apiflask as af
import arrow
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db
from ....lib import sanitizers
from .. import errors, schemas


bp = af.APIBlueprint("data extractions", __name__, url_prefix="/data_extractions")


class DataExtractionAPI(MethodView):
    @bp.doc(
        summary="get data extraction for a single study",
        responses={
            200: "successfully got data extraction record",
            403: "current app user forbidden to get data extraction record",
            404: "no data extraction with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.output(schemas.DataExtractionSchema)
    @jwtext.jwt_required()
    def get(self, id):
        current_user = jwtext.get_current_user()
        extracted_data = db.session.execute(
            sa.select(models.DataExtraction).filter_by(study_id=id)
        ).scalar_one_or_none()

        if not extracted_data:
            raise errors.NotFoundError(
                message=f"<DataExtraction(study_id={id})> not found"
            )

        # TODO: figure out if this is "better" approach
        # if current_user.is_admin is False and not any(
        #     review.id == extracted_data.review_id for review in current_user.reviews
        # ):
        if (
            current_user.is_admin is False
            and db.session.execute(
                current_user.review_user_assoc.select().filter_by(
                    review_id=extracted_data.review_id
                )
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get extracted data for this study"
            )

        current_app.logger.debug("got %s", extracted_data)
        return extracted_data

    @bp.doc(
        summary="modify data extraction for a single study",
        responses={
            200: "data extraction data was modified",
            403: "current app user forbidden to modify data extraction",
            404: "no data extraction with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(schemas.ExtractedItem(many=True), location="json")
    @bp.output(schemas.DataExtractionSchema)
    @jwtext.jwt_required()
    def put(self, id, json_data):
        current_user = jwtext.get_current_user()
        extracted_data = db.session.execute(
            sa.select(models.DataExtraction).filter_by(study_id=id)
        ).scalar_one_or_none()

        if not extracted_data:
            raise errors.NotFoundError(
                message=f"<DataExtraction(study_id={id})> not found"
            )

        review_id = extracted_data.review_id
        if (
            current_user.is_admin is False
            and db.session.execute(
                current_user.review_user_assoc.select().filter_by(review_id=review_id)
            ).one_or_none()
            is None
        ) or extracted_data.review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to modify extracted data for this study"
            )

        study = db.session.get(models.Study, id)
        assert study is not None  # type guard
        if study.data_extraction_status == "finished":
            raise errors.ForbiddenError(
                message=f'{extracted_data} already "finished", so can\'t be modified'
            )

        data_extraction_form = db.session.execute(
            sa.select(models.ReviewPlan.data_extraction_form).filter_by(id=review_id)
        ).one_or_none()
        if not data_extraction_form:
            raise errors.ForbiddenError(
                message=f"<ReviewPlan({review_id})> does not have a data extraction form"
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
        for item in json_data:
            label = item["label"]
            value = item["value"]
            if label not in labels_map:
                raise errors.BadRequestError(
                    message=f"label '{label}' invalid; available choices are {list(labels_map.keys())}"
                )
            field_type, allowed_values = labels_map[label]
            if field_type == "bool":
                if value in (1, True, "true", "t"):
                    validated_value = True
                elif value in (0, False, "false", "f"):
                    validated_value = False
                else:
                    raise errors.BadRequestError(
                        message=f'value "{value}" for label "{label}" invalid; must be {field_type}'
                    )
            elif field_type == "date":
                try:
                    validated_value = str(arrow.get(value).naive)
                except arrow.parser.ParserError:
                    raise errors.BadRequestError(
                        message=f'value "{value}" for label "{label}" invalid; must be ISO-formatted {field_type}'
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
                    raise errors.BadRequestError(
                        message=f"value '{value} for label '{label}' invalid; must be {field_type}"
                    )
            elif field_type == "select_one":
                if value not in allowed_values:
                    raise errors.BadRequestError(
                        message=f'value "{value}" for label "{label}" invalid; must be one of {allowed_values}'
                    )
                validated_value = value
            elif field_type == "select_many":
                validated_value = []
                for val in value:
                    if val not in allowed_values:
                        raise errors.BadRequestError(
                            message=f'value "{val}" for label "{label}" invalid; must be one of {allowed_values}'
                        )
                    validated_value.append(val)
            # TODO: implement this country validation
            elif field_type == "country":
                raise errors.BadRequestError(
                    message='"country" validation has not yet been implemented -- sorry!'
                )
            else:
                raise errors.BadRequestError(
                    message=f'field_type "{field_type}" is not valid'
                )
            extracted_data_map[label] = validated_value
        extracted_data.extracted_items = [
            {"label": label, "value": value}
            for label, value in extracted_data_map.items()
        ]
        # also update study's data_extraction_status
        study.data_extraction_status = "started"
        db.session.commit()

        current_app.logger.info("%s modified %s", current_user, extracted_data)
        return extracted_data

    @bp.doc(
        summary="delete data extraction for a single study",
        description=(
            "Since data extractions are automatically created upon fulltext inclusion "
            "and deleted upon fulltext exclusion, 'delete' here amounts to nulling out "
            "some or all of its non-required fields"
        ),
        responses={
            204: "successfully deleted (nulled) data extraction record",
            403: "current app user forbidden to delete data extraction record",
            404: "no data extraction with matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "labels": af.fields.DelimitedList(
                af.fields.String,
                delimiter=",",
                metadata={
                    "description": "comma-delimited list-as-string of data extraction labels to delete"
                },
            ),
        },
        location="query",
    )
    @bp.output({}, 204)
    @jwtext.jwt_required(fresh=True)
    def delete(self, id, query_data):
        labels = query_data.get("labels")
        current_user = jwtext.get_current_user()
        extracted_data = db.session.execute(
            sa.select(models.DataExtraction).filter_by(study_id=id)
        ).scalar_one_or_none()

        if not extracted_data:
            raise errors.NotFoundError(
                message=f"<DataExtraction(study_id={id})> not found"
            )

        if (
            current_user.is_admin is False
            and db.session.execute(
                current_user.review_user_assoc.select().filter_by(
                    review_id=extracted_data.review_id
                )
            ).one_or_none()
            is None
        ) or extracted_data.review.status == "frozen":
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to get extracted data for this study"
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
            study = db.session.get(models.Study, id)
            assert study is not None  # type guard
            study.data_extraction_status = "not_started"
        db.session.commit()

        current_app.logger.info(
            "%s deleted contents of %s", current_user, extracted_data
        )
        return ""


bp.add_url_rule("/<int:id>", view_func=DataExtractionAPI.as_view("data_extraction"))
