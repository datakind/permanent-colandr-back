"""Tests for the text metadata extractors."""
from unittest.mock import patch, MagicMock

from colandr.lib.extractors import review_metadata
from colandr.lib.extractors.metadata import Metadata
from colandr.lib.extractors.review_metadata import ReviewModel


class TestReviewMetadataExtraction:
    """Tests for the review_metadata extraction module."""

    @patch("sqlalchemy.orm.Session.execute")
    def test_review_model_init(self, mock_execute):
        """Test ReviewModel initialization and loading review plan."""
        mock_result = MagicMock()
        mock_review_plan = MagicMock()
        mock_review_plan.data_extraction_form = [
            {
                "label": "biome",
                "field_type": "select_one",
                "allowed_values": ["forest", "grassland", "desert"]
            },
            {
                "label": "species",
                "field_type": "select_many",
                "allowed_values": ["lion", "tiger", "bear"]
            },
            {
                "label": "area",
                "field_type": "float"  # Should be ignored as not a valid type
            }
        ]
        mock_result.scalar_one_or_none.return_value = mock_review_plan
        mock_execute.return_value = mock_result

        with patch("textacy.load_spacy_lang") as mock_load:
            mock_nlp = MagicMock()
            mock_load.return_value = mock_nlp

            model = ReviewModel(review_id=1)

            assert len(model.field_types) == 2
            assert model.field_types["biome"] == "select_one"
            assert model.field_types["species"] == "select_many"
            assert "area" not in model.field_types

            assert model.allowed_values["biome"] == ["forest", "grassland", "desert"]
            assert model.allowed_values["species"] == ["lion", "tiger", "bear"]

    @patch("colandr.lib.extractors.review_metadata.get_model_for_review")
    def test_extract_metadata(self, mock_get_model, app):
        """Test extract_metadata function."""
        mock_model = MagicMock()
        mock_model.extract_metadata.return_value = [
            Metadata(
                record="123",
                metadata="biome",
                value="forest",
                sentence="This is a forest biome.",
                sentence_location=5,
                confidence=0.85,
                confidence_level=2
            ),
            Metadata(
                record="123",
                metadata="species",
                value="lion",
                sentence="Lions live here.",
                sentence_location=10,
                confidence=0.9,
                confidence_level=3
            )
        ]
        mock_get_model.return_value = mock_model

        result = review_metadata.extract_metadata(
            record_id="123",
            review_id=1,
            text="Sample text about forest biomes and lions.",
            meta=None
        )

        assert len(result) == 2
        assert result[0].metadata == "biome"
        assert result[0].value == "forest"
        assert result[1].metadata == "species"
        assert result[1].value == "lion"

        # Test with metadata_type filter
        mock_get_model.reset_mock()
        mock_get_model.return_value = mock_model

        review_metadata.extract_metadata(
            record_id="123",
            review_id=1,
            text="Sample text about forest biomes and lions.",
            meta="biome"
        )

        mock_model.extract_metadata.assert_called_with(
            "123",
            "Sample text about forest biomes and lions.",
            threshold=app.config.get('METADATA_THRESHOLD')
        )

    @patch('colandr.lib.extractors.review_metadata.db.session')
    def test_process_text(self, mock_db_session):
        """Test the _process_text method with enhanced features."""
        model = ReviewModel(1)

        text = """
        This is a test document with several sentences.
        It contains information about the study conducted in Brazil.
        The researchers used surveys to collect data from 100 participants.
        """

        features = model._process_text(text)

        assert len(features) >= 2

        for feature in features:
            assert "text" in feature
            assert "position" in feature
            assert "index" in feature
            assert "sentence_length" in feature

            assert 0 <= feature["position"] <= 1
            assert feature["sentence_length"] > 0

        # Test with references section that should be excluded
        text = """
        This is the main content.

        References
        Smith, J. (2020). Some paper. Journal, 10(2), 123-145.
        """

        features = model._process_text(text)

        # Check we only have features from main content
        for feature in features:
            assert "Smith" not in feature["text"]
            assert "Journal" not in feature["text"]

    @patch('colandr.lib.extractors.review_metadata.db.session')
    def test_train_field_classifier(self, mock_db_session):
        """Test the _train_field_classifier method with enhanced features."""
        from river import compose

        model = ReviewModel(1)

        samples = [
            ("This study was conducted in Brazil using latest surveys.", "Brazil"),
            ("The research took place in Canada with experiments.", "Canada"),
            ("Data was collected in Brazil through observations.", "Brazil"),
            ("The most important study subjects were from the USA.", "USA"),
        ]

        model._train_field_classifier("country", samples)

        assert "country" in model.classifiers

        classifier = model.classifiers["country"]

        assert isinstance(classifier, compose.Pipeline)

        prediction = classifier.predict_proba_one("A new study from Brazil with 100 participants.")

        # Should predict Brazil with higher probability than others
        assert "Brazil" in prediction
        assert "Canada" in prediction
        assert "USA" in prediction
        assert prediction["Brazil"] > prediction["Canada"]
        assert prediction["Brazil"] > prediction["USA"]

        # Test with new country not in training set
        prediction = classifier.predict_proba_one("Research conducted in Mexico.")
        # Should still return probabilities for known classes
        assert "Brazil" in prediction
        assert "Canada" in prediction
        assert "USA" in prediction

    def test_split_references(self):
        """Test splitting document into main content and references."""
        # Test with references section
        text = """
        This is the main content.

        References
        Smith, J. (2020). Some paper title. Journal, 10(2), 123-145.
        Jones, A. (2019). Another paper. Conference Proceedings, pp. 234-245.
        """

        main, refs = review_metadata.split_references(text)
        assert "This is the main content." in main
        assert "References" not in main
        assert "Smith, J. (2020)" in refs

        # Test with works cited
        text = """
        This is the main content.

        Works Cited
        Smith, J. (2020). Some paper title. Journal, 10(2), 123-145.
        """

        main, refs = review_metadata.split_references(text)
        assert "This is the main content." in main
        assert "Works Cited" not in main
        assert "Smith, J. (2020)" in refs

        # Test with no references section
        text = "This is just content with no references section."
        main, refs = review_metadata.split_references(text)
        assert main == text
        assert refs == ""

        # Test with empty text
        assert review_metadata.split_references("") == ("", "")
        assert review_metadata.split_references(None) == ("", "")
