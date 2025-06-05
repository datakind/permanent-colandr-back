"""Metadata extraction from document full text."""

from collections import defaultdict
from dataclasses import dataclass
from typing import Any, Optional
import logging

from river import compose, feature_extraction, linear_model, multiclass, preprocessing
import textacy

from .metadata import Metadata


logger = logging.getLogger(__name__)


@dataclass
class Label:
    """Base class for labels."""
    label: str


@dataclass
class SingleValue(Label):
    """Label which contains a single value."""
    value: str


@dataclass
class MultiValue(Label):
    """Label which contains multiple values."""
    values: list[str]


@dataclass
class TrainingData:
    """Training data for a document."""
    record_id: int
    text_content: str
    labels: list[Label]


@dataclass
class RecordType:
    """Definition of a field from the review plan."""
    label: str
    field_type: str
    allowed_values: Optional[list[str]] = None


class ReviewModel:
    """
    Review-specific model for metadata extraction.
    """

    def __init__(self, review_id: int):
        """Initialize model for specific review."""
        self.review_id = review_id
        self.nlp = textacy.load_spacy_lang("en_core_web_md")  # TODO: implement language detection
        self.classifiers = {}
        self.training_counts = {}  # Track the number of training samples for each field

    def _process_text(self, text: str) -> list[dict[str, Any]]:
        """
        Process text into features for classification.

        Args:
            text: Full text content

        Returns:
            List of sentence features
        """
        # Split text into main content and references
        main_content, _ = split_references(text)

        doc = self.nlp(main_content)
        sentences = list(doc.sents)
        total_sentences = len(sentences)

        features = []
        for i, sent in enumerate(sentences):
            # Clean text and extract features
            sent_text = sent.text.strip()
            if len(sent_text) < 50:  # Skip very short sentences
                continue

            # Position in document (percentage)
            position = i / total_sentences if total_sentences else 0

            # Create feature dict
            features.append(
                {
                    "text": sent_text,
                    "position": position,
                    "index": i,
                    "sentence_length": len(sent),
                }
            )

        return features

    def train(self, training_data: list[TrainingData], min_samples: int = 40) -> bool:
        """
        Train classifiers for each metadata field.

        Args:
            training_data: List of training data records
            min_samples: Minimum number of training samples required to train a classifier

        Returns:
            bool: True if training was successful, False otherwise
        """
        if not training_data:
            logger.info("No training data for review %s", self.review_id)
            return False

        # Group training data by field
        field_data = defaultdict(list)
        for item in training_data:
            text = item.text_content
            for label in item.labels:
                if isinstance(label, SingleValue):
                    field_data[label.label].append((text, label.value))
                elif isinstance(label, MultiValue):
                    for value in label.values:
                        field_data[label.label].append((text, value))

        # Track training counts for each field
        old_training_counts = self.training_counts.copy()
        self.training_counts = {
            field: len(samples) for field, samples in field_data.items()
        }

        # Train a classifier for each field
        for field, samples in field_data.items():
            if len(samples) < min_samples:
                logger.info(
                    "Not enough training data for field %s (only %s samples, need %s)",
                    field,
                    len(samples),
                    min_samples,
                )
                continue

            # Create a classifier
            self._train_field_classifier(field, samples)

        logger.info(
            "Trained classifiers for review %s: %s",
            self.review_id,
            list(self.classifiers.keys()),
        )
        logger.info(
            "Training counts: %s, previous counts: %s",
            self.training_counts,
            old_training_counts,
        )
        return len(self.classifiers) > 0

    def _train_field_classifier(self, field: str, samples: list[tuple[str, str]]):
        """
        Train a classifier for a specific field.

        Args:
            field: Field name
            samples: List of (text, value) tuples
        """
        # Create a Multi-class classifier using River
        model = compose.Pipeline(
            ("tfidf", feature_extraction.TFIDF(lowercase=True)),
            ("normalize", preprocessing.StandardScaler()),
            (
                "classifier",
                multiclass.OneVsRestClassifier(
                    linear_model.LogisticRegression(l2=0.01)
                ),
            ),
        )

        # Process each document
        for text, value in samples:
            sentences = self._process_text(text)
            for sentence in sentences:
                # Train the model on each sentence
                model.learn_one(sentence["text"], value)

        # Store the classifier
        self.classifiers[field] = model

    def extract_metadata(
        self, record_id: int, text: str, threshold: float = 0.5
    ) -> list[Metadata]:
        """
        Extract metadata from text.

        Args:
            record_id: Record identifier
            text: Full text content
            threshold: Confidence threshold

        Returns:
            List of extracted metadata
        """
        if not self.classifiers:
            return []

        sentences = self._process_text(text)
        results = []

        # Process each field
        for field, classifier in self.classifiers.items():
            field_results = []

            # For each sentence, predict the field value
            for sentence in sentences:
                # Get predictions with probabilities
                prediction = classifier.predict_proba_one(sentence["text"])

                # Sort by probability
                sorted_preds = sorted(
                    prediction.items(), key=lambda x: x[1], reverse=True
                )

                # Add results above threshold
                for value, prob in sorted_preds:
                    if prob >= threshold:
                        confidence_level = self._get_confidence_level(threshold, prob)
                        field_results.append(
                            Metadata(
                                record=record_id,
                                metadata=field,
                                value=value,
                                sentence=sentence["text"],
                                sentence_location=sentence["index"],
                                confidence=prob,
                                confidence_level=confidence_level,
                            )
                        )

            # Take top 3 predictions for this field
            results.extend(
                sorted(field_results, key=lambda x: x.confidence, reverse=True)[:3]
            )

        return sorted(results, key=lambda x: x.confidence, reverse=True)

    def _get_confidence_level(self, threshold: float, prob: float) -> int:
        """
        Calculate confidence level (0-3) based on probability.

        Args:
            threshold: Minimum threshold
            prob: Prediction probability

        Returns:
            Integer confidence level from 0 to 3
        """
        if prob < threshold:
            return -1

        # Divide the range from threshold to 1.0 into 3 parts
        one_third = (1.0 - threshold) / 3

        if prob >= threshold + (2 * one_third):
            return 3  # High confidence
        if prob >= threshold + one_third:
            return 2  # Medium confidence
        return 1  # Low confidence

    def compare_and_train(
        self,
        training_data: list[TrainingData],
        min_samples: int = 40,
        increase_requirement: int = 5
    ) -> tuple[bool, "ReviewModel"]:
        """
        Compare current training data with previous data and retrain if necessary.

        Args:
            training_data: New training data to compare against
            min_samples: Minimum number of samples needed to train
            increase_requirement: Number of new samples needed to trigger retraining

        Returns:
            Tuple of (whether model was retrained, the current model)
        """
        if not training_data:
            logger.info("No training data for review %s", self.review_id)
            return False, self

        # Count labels by field
        current_counts = defaultdict(int)
        for item in training_data:
            for label in item.labels:
                if isinstance(label, SingleValue):
                    current_counts[label.label] += 1
                elif isinstance(label, MultiValue):
                    current_counts[label.label] += len(label.values)

        # Filter fields with enough samples
        current_counts_filtered = {
            f: count for f, count in current_counts.items() if count >= min_samples
        }

        if not current_counts_filtered:
            logger.info("No fields have enough training data (min %s)", min_samples)
            return False, self

        prev_max_count = (
            max(self.training_counts.values()) if self.training_counts else 0
        )
        current_max_count = max(current_counts_filtered.values())

        # If we have enough new samples, retrain
        if current_max_count >= prev_max_count + increase_requirement:
            logger.info(
                "Retraining model due to increased training data: %s >= %s + %s",
                current_max_count,
                prev_max_count,
                increase_requirement,
            )
            self.train(training_data, min_samples=min_samples)
            return True, self

        logger.info(
            "Not retraining model: %s < %s + %s",
            current_max_count,
            prev_max_count,
            increase_requirement,
        )
        return False, self


def split_references(text: str) -> tuple[str, str]:
    """
    Split document text into main content and references sections.

    Args:
        text: The full document text

    Returns:
        Tuple of (main_content, references_section)
    """
    if not text:
        return "", ""

    lines = text.split("\n")
    main_content = []
    references = []

    in_references = False

    for line in lines:
        # Check for common reference section headers
        if not in_references:
            line_lower = line.lower().strip()
            if line_lower == "references":
                in_references = True
                continue
            if line_lower.startswith("works cited") or line_lower.startswith(
                "literature cited"
            ):
                in_references = True
                continue

        # Add line to appropriate section
        if in_references:
            references.append(line)
        else:
            main_content.append(line)

    return "\n".join(main_content), "\n".join(references)
