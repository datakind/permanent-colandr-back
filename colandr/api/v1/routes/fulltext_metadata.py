import apiflask as af
import flask_jwt_extended as jwtext
import sqlalchemy as sa
from flask import current_app
from flask.views import MethodView

from .... import models
from ....extensions import db, review_model_cache
from ....lib.extractors.review_model import (
    MultiValue,
    RecordType,
    ReviewModel,
    SingleValue,
    TrainingData,
)
from .. import errors, schemas


bp = af.APIBlueprint("fulltext metadata", __name__, url_prefix="/fulltexts")


class FulltextMetadataAPI(MethodView):
    @bp.doc(
        summary="extract metadata from fulltext content",
        responses={
            200: "successfully extracted metadata from fulltext",
            403: "current app user forbidden to access this fulltext",
            404: "no fulltext matching id was found",
        },
        security="TokenAuth",
    )
    @bp.input(
        {
            "meta": af.fields.String(
                required=False, description="optional metadata type to filter results"
            )
        },
        location="query",
    )
    @bp.output(schemas.MetadataSchema(many=True))
    @jwtext.jwt_required()
    def get(self, id, query_data):
        meta = query_data.get("meta")
        current_user = jwtext.get_current_user()
        study = db.session.get(models.Study, id)

        if not study:
            raise errors.NotFoundError(message=f"<Study(id={id})> not found")

        if (
            current_user.is_admin is False
            and study.review.review_user_assoc.filter_by(
                user_id=current_user.id
            ).one_or_none()
            is None
        ):
            raise errors.ForbiddenError(
                message=f"{current_user} forbidden to access this fulltext"
            )

        if not study.fulltext or not study.fulltext.get("text_content"):
            current_app.logger.debug("no fulltext available for %s", study)
            return []

        text_content = study.fulltext.get("text_content")
        assert isinstance(text_content, str)  # type guard
        model = _get_model_for_review(study.review_id)
        threshold = current_app.config.get("METADATA_THRESHOLD", 0.65)
        metadatas = model.extract_metadata(id, text_content, threshold=threshold)
        # filter by metadata type if specified
        if meta:
            metadatas = [m for m in metadatas if m.metadata == meta]

        current_app.logger.debug(
            "%s got %s metadatas for %s", current_user, len(metadatas), study
        )
        return metadatas


def _get_field_definitions(review_id: int) -> list[RecordType]:
    """
    Get field definitions from the review plan.

    Args:
        review_id: Review identifier

    Returns:
        List of field definitions
    """
    stmt = sa.select(models.ReviewPlan).where(models.ReviewPlan.id == review_id)
    review_plan = db.session.execute(stmt).scalar_one_or_none()

    if not review_plan or not review_plan.data_extraction_form:
        return []

    field_defs = []
    for field in review_plan.data_extraction_form:
        field_type = field.get("field_type")
        label = field.get("label")
        allowed_values = field.get("allowed_values")

        if field_type and label:
            field_defs.append(
                RecordType(
                    label=label, field_type=field_type, allowed_values=allowed_values
                )
            )

    return field_defs


def _get_training_data(review_id: int) -> list[TrainingData]:
    """
    Get training data for a review.

    Args:
        review_id: Review identifier

    Returns:
        List of training data records
    """
    field_defs = _get_field_definitions(review_id)

    valid_types = {"select_one", "select_many"}
    valid_labels = {fd.label for fd in field_defs if fd.field_type in valid_types}

    stmt = (
        sa.select(models.Study, models.DataExtraction)
        .join(models.DataExtraction, models.Study.id == models.DataExtraction.study_id)
        .where(models.Study.review_id == review_id)
        .where(models.Study.fulltext.is_not(None))
        .where(models.DataExtraction.extracted_items.is_not(None))
    )
    result = db.session.execute(stmt)
    training_data = []

    for study, data_extraction in result:
        if not study.fulltext or not study.fulltext.get("text_content"):
            continue

        text_content = study.fulltext.get("text_content")
        labels = []

        for item in data_extraction.extracted_items or []:
            label = item.get("label")
            value = item.get("value")

            if not label or not value:
                continue

            if label not in valid_labels:
                continue

            # Handle select_many fields which could have multiple values
            if isinstance(value, list):
                if value:  # Skip empty lists
                    labels.append(
                        MultiValue(label=label, values=[v for v in value if v])
                    )
            else:
                # Handle select_one fields
                labels.append(SingleValue(label=label, value=str(value)))

        if labels:
            training_data.append(
                TrainingData(
                    record_id=study.id, text_content=text_content, labels=labels
                )
            )

    return training_data


def _get_model_for_review(review_id: int) -> ReviewModel:
    """
    Get or create a model for a specific review.
    Uses cache to avoid retraining.

    Args:
        review_id: The review ID

    Returns:
        ReviewModel if successful, None otherwise
    """
    min_to_train = current_app.config.get("METADATA_MIN_TO_TRAIN", 40)
    increase_to_retrain = current_app.config.get("METADATA_INCREASE_TO_RETRAIN", 5)

    training_data = _get_training_data(review_id)

    # Try to get from cache first
    model: ReviewModel = review_model_cache.get(str(review_id))

    if model is not None:
        # Check if model needs retraining
        retrained, model = model.compare_and_train(
            training_data=training_data,
            min_samples=min_to_train,
            increase_requirement=increase_to_retrain,
        )

        if retrained:
            review_model_cache.set(str(review_id), model)

        return model

    # Create new model
    model = ReviewModel()

    if model.train(training_data, min_samples=min_to_train):
        review_model_cache.set(str(review_id), model)

    return model


bp.add_url_rule(
    "/<int:id>/metadata", view_func=FulltextMetadataAPI.as_view("fulltext_metadata")
)
