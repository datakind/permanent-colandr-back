"""Tests for the text metadata extractors."""

from unittest.mock import MagicMock, patch

import numpy as np
import pandas as pd
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer

from colandr.lib.extractors.review_model import ReviewModel, SingleValue, TrainingData


class TestReviewModel:
    """Tests for the ReviewModel class."""

    def _create_mock_sentence(self, text, has_verb=True):
        """Helper to create a mock spaCy sentence with POS tags."""
        mock_sent = MagicMock()
        mock_sent.text = text

        mock_tokens = []
        for word in text.split():
            token = MagicMock()
            # A simple rule for the test: if the word is 'is', it's a verb
            token.pos_ = "VERB" if has_verb and word.lower() == "is" else "NOUN"
            mock_tokens.append(token)

        mock_sent.__iter__ = MagicMock(return_value=iter(mock_tokens))
        return mock_sent

    def test_is_valid_sentence(self):
        """Test the _is_valid_sentence helper directly."""
        model = ReviewModel()

        valid_sent = self._create_mock_sentence(
            "This is a perfectly valid and long sentence for model."
        )
        short_sent = self._create_mock_sentence("This sentence is too short.")
        no_verb_sent = self._create_mock_sentence(
            "A long title fragment with no actual verb.", has_verb=False
        )
        keyword_sent = self._create_mock_sentence(
            "A long sentence that contains a forbidden keyword like DEBUG."
        )

        assert model._is_valid_sentence(valid_sent) is True
        assert model._is_valid_sentence(short_sent) is False
        assert model._is_valid_sentence(no_verb_sent) is False
        assert model._is_valid_sentence(keyword_sent) is False
        assert model._is_valid_sentence(None) is False

    def test_train_success(self):
        """Test the train method succeeds with sufficient data."""
        model = ReviewModel()
        training_data = [
            TrainingData(
                1, "This is a valid sentence.", labels=[SingleValue("biome", "forest")]
            )
        ] * 10  # 10 labels

        with patch(
            "colandr.lib.extractors.review_model.Pipeline"
        ) as mock_pipeline_class:
            mock_pipeline_instance = MagicMock()
            mock_pipeline_class.return_value = mock_pipeline_instance

            with patch.object(model, "_create_sentence_features") as mock_prepare:
                mock_x = pd.DataFrame([{"text": "mock"}])
                mock_y = np.array([[1]])
                mock_prepare.return_value = (mock_x, mock_y)

                result = model.train(training_data, min_samples=5)

                assert result is True
                mock_prepare.assert_called_once_with(training_data)
                mock_pipeline_instance.fit.assert_called_once_with(mock_x, mock_y)
                assert model.pipeline is not None
                assert model.last_training_size == 10

    def test_train_insufficient_data(self):
        """Test that training is skipped if data is insufficient."""
        model = ReviewModel()
        training_data = [TrainingData(1, "text", labels=[SingleValue("a", "b")])]

        with patch.object(model, "_create_sentence_features") as mock_prepare:
            result = model.train(training_data, min_samples=40)
            assert result is False
            mock_prepare.assert_not_called()

    def test_compare_and_train_triggers_retrain(self):
        """Test compare_and_train triggers a new training session when required."""
        model = ReviewModel()
        model.last_training_size = 10

        training_data = [
            TrainingData(i, "text", labels=[SingleValue("a", "b")]) for i in range(16)
        ]

        with patch.object(model, "train") as mock_train:
            mock_train.return_value = True
            retrained, _ = model.compare_and_train(
                training_data, min_samples=10, increase_requirement=5
            )
            assert retrained is True
            mock_train.assert_called_once_with(training_data, min_samples=10)

    def test_compare_and_train_skips_retrain(self):
        """Test compare_and_train skips training when the increase is not sufficient."""
        model = ReviewModel()
        model.last_training_size = 10

        training_data = [
            TrainingData(i, "text", labels=[SingleValue("a", "b")]) for i in range(14)
        ]

        with patch.object(model, "train") as mock_train:
            retrained, _ = model.compare_and_train(
                training_data, min_samples=10, increase_requirement=5
            )
            assert retrained is False
            mock_train.assert_not_called()

    @patch("colandr.lib.extractors.review_model.process_texts_into_docs")
    def test_extract_metadata(self, mock_process_texts):
        """Test the full metadata extraction integration."""
        model = ReviewModel()

        mock_pipeline = MagicMock(spec=Pipeline)
        mock_probs = [
            np.array([[0.1, 0.9]]),  # Probs for label 1 (class 0, class 1)
            np.array([[0.6, 0.4]]),  # Probs for label 2 (class 0, class 1)
        ]
        mock_pipeline.predict_proba.return_value = mock_probs
        model.pipeline = mock_pipeline

        mock_binarizer = MagicMock(spec=MultiLabelBinarizer)
        mock_binarizer.classes_ = ["biome:forest", "biome:desert"]
        model.label_binarizer = mock_binarizer

        sent_text = "This is a valid long sentence about forest biomes."
        mock_sent = self._create_mock_sentence(sent_text, has_verb=True)
        mock_doc = MagicMock()
        mock_doc.sents = [mock_sent]
        mock_process_texts.return_value = iter([mock_doc])

        results = model.extract_metadata(123, "some input text", threshold=0.5)

        mock_process_texts.assert_called_once()
        assert len(results) == 1
        result = results[0]
        assert result.record == 123
        assert result.metadata == "biome"
        assert result.value == "forest"
        assert result.confidence == 0.9
        assert result.sentence == sent_text

    def test_split_references(self):
        """Test splitting document into main content and references."""
        model = ReviewModel()
        text = "Main content.\n\nReferences\n1. Smith, J."
        main, refs = model._split_references(text)
        assert main.strip() == "Main content."
        assert refs == "1. Smith, J."

        text_no_refs = "Main content only."
        main, refs = model._split_references(text_no_refs)
        assert main == text_no_refs
        assert refs == ""

        assert model._split_references("") == ("", "")
