from unittest.mock import patch, MagicMock
import pytest

import flask
from lib.extractors.metadata import Metadata


@pytest.mark.usefixtures("db_session")
class TestFulltextMetadataResource:
    @pytest.mark.parametrize(
        ["id_", "params", "status_code"],
        [
            (1, {}, 200),
            (2, {}, 200),
            (1, {"meta": "biome"}, 200),
            (999, {}, 404),
        ],
    )
    @patch("colandr.apis.resources.fulltext_metadata._get_model_for_review")
    def test_get(self, mock_get_model, id_, params, status_code, app, client, admin_headers):
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model if status_code == 200 else None
        mock_model.extract_metadata.return_value = []

        with app.test_request_context():
            url = flask.url_for("fulltext_metadata_fulltext_metadata_resource", id=id_, **params)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code

        if 200 <= status_code < 300:
            data = response.json
            assert isinstance(data, list)

            if status_code == 200 and id_ in (1, 2):
                if id_ == 1:
                    mock_model.extract_metadata.assert_called_with(
                        id_,
                        "This is an example text in English.",
                        threshold=app.config.get("METADATA_THRESHOLD")
                    )

    @patch("colandr.apis.resources.fulltext_metadata._get_model_for_review")
    def test_get_with_mock(self, mock_get_model, app, client, admin_headers):
        """Test getting metadata with mocked extraction."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        mock_metadata = [
            Metadata(
                record=1,
                metadata="biome",
                value="forest",
                sentence="This study was conducted in a tropical forest.",
                sentence_location=8,
                confidence=0.85,
                confidence_level=2
            ),
            Metadata(
                record=1,
                metadata="species",
                value="lion",
                sentence="We observed several lion populations.",
                sentence_location=15,
                confidence=0.92,
                confidence_level=3
            )
        ]
        mock_model.extract_metadata.return_value = mock_metadata

        with app.test_request_context():
            url = flask.url_for("fulltext_metadata_fulltext_metadata_resource", id=1)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200

        metadata_data = response.json
        assert len(metadata_data) == 2

        assert metadata_data[0]["record"] == 1
        assert "metadata" in metadata_data[0]
        assert "value" in metadata_data[0]
        assert "sentence" in metadata_data[0]
        assert "sentence_location" in metadata_data[0]
        assert "confidence" in metadata_data[0]
        assert "confidence_level" in metadata_data[0]

        mock_model.extract_metadata.assert_called_with(
            1,
            "This is an example text in English.",
            threshold=app.config.get("METADATA_THRESHOLD")
        )

    @patch("colandr.apis.resources.fulltext_metadata._get_model_for_review")
    def test_get_filtered_with_mock(self, mock_get_model, app, client, admin_headers):
        """Test getting filtered metadata with mocked extraction."""
        mock_model = MagicMock()
        mock_get_model.return_value = mock_model

        mock_metadata = [
            Metadata(
                record=1,
                metadata="biome",
                value="forest",
                sentence="This study was conducted in a tropical forest.",
                sentence_location=8,
                confidence=0.85,
                confidence_level=2
            )
        ]
        mock_model.extract_metadata.return_value = mock_metadata

        with app.test_request_context():
            params = {"meta": "biome"}
            url = flask.url_for("fulltext_metadata_fulltext_metadata_resource", id=1, **params)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200

        metadata_data = response.json
        assert len(metadata_data) == 1
        assert metadata_data[0]["metadata"] == "biome"

        mock_model.extract_metadata.assert_called_with(
            1,
            "This is an example text in English.",
            threshold=app.config.get("METADATA_THRESHOLD")
        )

    @patch("colandr.apis.resources.fulltext_metadata._get_training_data")
    def test_get_model_for_review(self, mock_get_training_data, app):
        """Test the get_model_for_review function."""
        from colandr.lib.extractors.review_metadata import TrainingData, SingleValue
        from colandr.apis.resources.fulltext_metadata import _get_model_for_review

        mock_training = [
            TrainingData(
                record_id=1,
                text_content="This is a forest biome with trees.",
                labels=[SingleValue(label="biome", value="forest")]
            ),
            TrainingData(
                record_id=2,
                text_content="Desert regions have hot climate.",
                labels=[SingleValue(label="biome", value="desert")]
            )
        ]

        # Add enough training data to meet minimum requirements
        for i in range(38):
            mock_training.append(
                TrainingData(
                    record_id=i+3,
                    text_content=f"Sample {i} forest text content",
                    labels=[SingleValue(label="biome", value="forest")]
                )
            )

        mock_get_training_data.return_value = mock_training

        # Test with cache miss
        with patch("colandr.extensions.review_model_cache.get") as mock_cache_get:
            with patch("colandr.extensions.review_model_cache.set") as mock_cache_set:
                mock_cache_get.return_value = None

                with app.test_request_context():
                    model = _get_model_for_review(1)

                # Should create new model
                assert model.review_id == 1
                mock_get_training_data.assert_called_once_with(1)
                mock_cache_set.assert_called_once()

        # Test with cache hit and no retraining
        with patch("colandr.extensions.review_model_cache.get") as mock_cache_get:
            with patch("colandr.extensions.review_model_cache.set") as mock_cache_set:
                mock_model = MagicMock()
                mock_model.compare_and_train.return_value = (False, mock_model)
                mock_cache_get.return_value = mock_model

                with app.test_request_context():
                    model = _get_model_for_review(1)

                # Should return cached model without setting cache again
                assert model == mock_model
                mock_cache_set.assert_not_called()

    @patch("colandr.apis.resources.fulltext_metadata._get_field_definitions")
    def test_get_training_data_filtering(self, mock_get_field_definitions, app, db_session):
        """Test get_training_data function properly filters labels based on field types."""
        from colandr.apis.resources.fulltext_metadata import _get_training_data
        from colandr.lib.extractors.review_metadata import RecordType

        mock_field_defs = [
            RecordType(label="biome", field_type="select_one", allowed_values=["forest", "desert"]),
            RecordType(label="species", field_type="select_many", allowed_values=["lion", "tiger"]),
            RecordType(label="area", field_type="float"),
            RecordType(label="notes", field_type="text")
        ]
        mock_get_field_definitions.return_value = mock_field_defs

        with patch("colandr.apis.resources.fulltext_metadata.db.session.execute") as mock_execute:
            mock_study = MagicMock()
            mock_study.id = 1
            mock_study.review_id = 1
            mock_study.fulltext = {"text_content": "Test content"}

            mock_extraction = MagicMock()
            mock_extraction.extracted_items = [
                {"label": "biome", "value": "forest"},
                {"label": "species", "value": ["lion", "tiger"]},
                {"label": "area", "value": "100.5"},
                {"label": "notes", "value": "Some text notes"}
            ]

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
