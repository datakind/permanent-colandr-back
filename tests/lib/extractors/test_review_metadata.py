"""Tests for the text metadata extractors."""
from unittest.mock import patch, MagicMock

from colandr.lib.extractors import review_metadata
from colandr.lib.extractors.review_metadata import (
    ReviewModel, TrainingData, SingleValue, MultiValue
)


class TestReviewMetadataExtraction:
    """Tests for the review_metadata extraction module."""

    def test_process_text(self):
        """Test the _process_text method with enhanced features."""
        with patch("textacy.load_spacy_lang") as mock_load:
            mock_nlp = MagicMock()

            mock_sent1 = MagicMock()
            mock_sent1.text = "This is a test document with several long sentences."
            mock_sent1.__len__ = lambda x: 10

            mock_sent2 = MagicMock()
            mock_sent2.text = "It contains information about the study conducted in Brazil."
            mock_sent2.__len__ = lambda x: 15

            mock_sents = [mock_sent1, mock_sent2]
            mock_doc = MagicMock()
            mock_doc.sents = mock_sents

            mock_nlp.return_value = mock_doc
            mock_load.return_value = mock_nlp

            model = ReviewModel(1)

            text = """
            This is a test document with several long sentences.
            It contains information about the study conducted in Brazil.
            """

            features = model._process_text(text)

            assert len(features) == 2

            for feature in features:
                assert "text" in feature
                assert "position" in feature
                assert "index" in feature
                assert "sentence_length" in feature

                assert 0 <= feature["position"] <= 1
                assert feature["sentence_length"] > 0

    def test_train_model(self):
        """Test the train method with training data."""
        with patch("textacy.load_spacy_lang") as mock_load:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            mock_sent = MagicMock()
            mock_sent.text = "Test sentence"
            mock_sent.__len__ = lambda x: 2
            mock_doc.sents = [mock_sent]
            mock_nlp.return_value = mock_doc
            mock_load.return_value = mock_nlp

            # Mock River components
            with patch("river.compose.Pipeline") as mock_pipeline:
                mock_classifier = MagicMock()
                mock_pipeline.return_value = mock_classifier

                # Create model and training data
                model = ReviewModel(1)
                training_data = [
                    TrainingData(
                        record_id=1,
                        text_content="This is a forest biome with many tropic trees and bushes.",
                        labels=[SingleValue(label="biome", value="forest")]
                    ),
                    TrainingData(
                        record_id=2,
                        text_content="Desert regions have limited precipitation and poor flora.",
                        labels=[SingleValue(label="biome", value="desert")]
                    ),
                    TrainingData(
                        record_id=3,
                        text_content="Lions and tigers are apex predators which controls area.",
                        labels=[
                            MultiValue(label="species", values=["lion", "tiger"])
                        ]
                    )
                ]

                result = model.train(training_data, min_samples=1)

                assert result is True
                assert mock_pipeline.call_count > 0
                assert len(model.classifiers) > 0

    def test_compare_and_train(self):
        """Test the compare_and_train method."""
        with patch("textacy.load_spacy_lang") as mock_load:
            mock_nlp = MagicMock()
            mock_doc = MagicMock()
            mock_sent = MagicMock()
            mock_sent.text = "Test sentence"
            mock_sent.__len__ = lambda x: 2
            mock_doc.sents = [mock_sent]
            mock_nlp.return_value = mock_doc
            mock_load.return_value = mock_nlp

            model = ReviewModel(1)
            model.training_counts = {"biome": 5}

            training_data = []
            for i in range(20):
                training_data.append(
                    TrainingData(
                        record_id=i,
                        text_content=f"Sample {i} about forest biomes",
                        labels=[SingleValue(label="biome", value="forest")]
                    )
                )

            with patch.object(model, 'train') as mock_train:
                mock_train.return_value = True

                retrained, updated_model = model.compare_and_train(
                    training_data=training_data,
                    min_samples=5,
                    increase_requirement=5
                )

                assert retrained is True
                assert mock_train.called
                mock_train.assert_called_once_with(training_data, min_samples=5)

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
