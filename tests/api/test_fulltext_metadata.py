"""Tests for the fulltext metadata API."""

from unittest.mock import MagicMock, patch

import pytest

from colandr.lib.extractors.metadata import Metadata
from colandr.lib.extractors.review_model import RecordType, SingleValue, TrainingData

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

FULLTEXT_METADATA_API_ENDPOINT = "fulltext_metadata.fulltext_metadata"
PATCH_FUNC_PATH = "colandr.api.v1.routes.fulltext_metadata"

FULLTEXT_TEXT = "This is a factory-provided example text."


@pytest.fixture
def graph(db_session):
    """A review with two studies, each carrying an explicit fulltext text.

    The acting user is the world's admin, who needs no team association.
    The route only reads ``study.fulltext["text_content"]``, so no on-disk file is needed.
    """
    review = factories.create_review(db_session)
    fulltexts = [{"text_content": FULLTEXT_TEXT}, {"text_content": FULLTEXT_TEXT}]
    s1, s2 = factories.create_studies(db_session, 2, review=review, fulltexts=fulltexts)
    return {"s1": s1, "s2": s2}


class TestFulltextMetadataAPI:
    @pytest.mark.parametrize(
        ["study_key", "params", "status_code"],
        [
            ("s1", {}, 200),
            ("s2", {}, 200),
            ("s1", {"meta": "biome"}, 200),
            (None, {}, 404),
        ],
    )
    @patch(f"{PATCH_FUNC_PATH}._get_model_for_review")
    def test_get(self, mock_get_model, study_key, params, status_code, app, api, graph):
        """Get metadata extracted from a study's fulltext text."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model if status_code == 200 else None
        mock_model.extract_metadata.return_value = []

        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.get(FULLTEXT_METADATA_API_ENDPOINT, id=study_id, **params)
        assert response.status_code == status_code

        if 200 <= status_code < 300:
            assert response.json == []
            mock_model.extract_metadata.assert_called_with(
                study_id,
                FULLTEXT_TEXT,
                threshold=app.config.get("METADATA_THRESHOLD"),
            )

    @patch(f"{PATCH_FUNC_PATH}._get_model_for_review")
    def test_get_with_mock(self, mock_get_model, app, api, graph):
        """Get metadata extracted from one study by a mocked model."""
        study = graph["s1"]
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.extract_metadata.return_value = [
            Metadata(
                record=study.id,
                metadata="biome",
                value="forest",
                sentence="This study was conducted in a tropical forest.",
                sentence_location=8,
                confidence=0.85,
                confidence_level=2,
            ),
            Metadata(
                record=study.id,
                metadata="species",
                value="lion",
                sentence="We observed several lion populations.",
                sentence_location=15,
                confidence=0.92,
                confidence_level=3,
            ),
        ]

        response = api.get(FULLTEXT_METADATA_API_ENDPOINT, id=study.id)
        assert response.status_code == 200

        metadata_data = response.json
        assert len(metadata_data) == 2
        # the extracted records name the study they came from, and nothing else
        assert [record["record"] for record in metadata_data] == [study.id, study.id]
        for record in metadata_data:
            assert record["metadata"] in {"biome", "species"}
            for field in (
                "value",
                "sentence",
                "sentence_location",
                "confidence",
                "confidence_level",
            ):
                assert field in record

        mock_model.extract_metadata.assert_called_with(
            study.id,
            FULLTEXT_TEXT,
            threshold=app.config.get("METADATA_THRESHOLD"),
        )

    @patch(f"{PATCH_FUNC_PATH}._get_model_for_review")
    def test_get_filtered_with_mock(self, mock_get_model, app, api, graph):
        """Get metadata filtered to one metadata type, from a mocked model."""
        study = graph["s1"]
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model
        mock_model.extract_metadata.return_value = [
            Metadata(
                record=study.id,
                metadata="biome",
                value="forest",
                sentence="This study was conducted in a tropical forest.",
                sentence_location=8,
                confidence=0.85,
                confidence_level=2,
            )
        ]

        response = api.get(FULLTEXT_METADATA_API_ENDPOINT, id=study.id, meta="biome")
        assert response.status_code == 200

        metadata_data = response.json
        assert len(metadata_data) == 1
        assert metadata_data[0]["metadata"] == "biome"

        mock_model.extract_metadata.assert_called_with(
            study.id,
            FULLTEXT_TEXT,
            threshold=app.config.get("METADATA_THRESHOLD"),
        )

    @pytest.mark.skip(reason="this test's mocking needs to be fixed")
    @patch(f"{PATCH_FUNC_PATH}._get_training_data")
    def test_get_model_for_review(self, mock_get_training_data, app):
        """Test the get_model_for_review function."""
        from colandr.apis.resources.fulltext_metadata import _get_model_for_review

        mock_training = [
            TrainingData(
                record_id=1,
                text_content="This is a forest biome with trees.",
                labels=[SingleValue(label="biome", value="forest")],
            ),
            TrainingData(
                record_id=2,
                text_content="Desert regions have hot climate.",
                labels=[SingleValue(label="biome", value="desert")],
            ),
        ]

        # Add enough training data to meet minimum requirements
        for i in range(38):
            mock_training.append(
                TrainingData(
                    record_id=i + 3,
                    text_content=f"Sample {i} forest text content",
                    labels=[SingleValue(label="biome", value="forest")],
                )
            )

        mock_get_training_data.return_value = mock_training

        mock_model = MagicMock()

        # Test with cache miss
        with (
            patch("colandr.extensions.review_model_cache.get") as mock_cache_get,
            patch("colandr.extensions.review_model_cache.set") as mock_cache_set,
            patch(f"{PATCH_FUNC_PATH}.ReviewModel") as mock_model_class,
        ):
            mock_cache_get.return_value = None
            mock_model_class.return_value = mock_model
            mock_model.train.return_value = True

            with app.test_request_context():
                model = _get_model_for_review(1)

            # Should create new model
            mock_get_training_data.assert_called_once_with(1)
            mock_cache_set.assert_called_once()

        # Test with cache hit and no retraining
        with patch("colandr.extensions.review_model_cache.get") as mock_cache_get:
            with patch("colandr.extensions.review_model_cache.set") as mock_cache_set:
                mock_model.compare_and_train.return_value = (False, mock_model)
                mock_cache_get.return_value = mock_model

                with app.test_request_context():
                    model = _get_model_for_review(1)

                # Should return cached model without setting cache again
                assert model == mock_model
                mock_cache_set.assert_not_called()

    @pytest.mark.skip(reason="this test's mocking needs to be fixed")
    @patch(f"{PATCH_FUNC_PATH}._get_field_definitions")
    def test_get_training_data_filtering(
        self, mock_get_field_definitions, app, db_session
    ):
        """Test get_training_data function properly filters labels based on field types."""
        from colandr.apis.resources.fulltext_metadata import _get_training_data

        mock_field_defs = [
            RecordType(
                label="biome",
                field_type="select_one",
                allowed_values=["forest", "desert"],
            ),
            RecordType(
                label="species",
                field_type="select_many",
                allowed_values=["lion", "tiger"],
            ),
            RecordType(label="area", field_type="float"),
            RecordType(label="notes", field_type="text"),
        ]
        mock_get_field_definitions.return_value = mock_field_defs

        with patch(f"{PATCH_FUNC_PATH}.db.session.execute") as mock_execute:
            mock_study = MagicMock()
            mock_study.id = 1
            mock_study.review_id = 1
            mock_study.fulltext = {"text_content": "Test content"}

            mock_extraction = MagicMock()
            mock_extraction.extracted_items = [
                {"label": "biome", "value": "forest"},
                {"label": "species", "value": ["lion", "tiger"]},
                {"label": "area", "value": "100.5"},
                {"label": "notes", "value": "Some text notes"},
            ]

            # TODO: burton, figure this out
            # mock_scalar_one_or_none = MagicMock()
            # mock_scalar_one_or_none.return_value = [(mock_study, mock_extraction)]
            # mock_execute.return_value = mock_scalar_one_or_none
            mock_result = [(mock_study, mock_extraction)]
            mock_execute.return_value = mock_result

            training_data = _get_training_data(1)

            assert len(training_data) == 1

            labels = training_data[0].labels
            label_names = [label.label for label in labels]
            assert "biome" in label_names
            assert "species" in label_names
            assert "area" not in label_names
            assert "notes" not in label_names

            for label in labels:
                if label.label == "biome":
                    assert isinstance(label.value, str)
                    assert label.value == "forest"
                elif label.label == "species":
                    assert isinstance(label.values, list)
                    assert set(label.values) == {"lion", "tiger"}
