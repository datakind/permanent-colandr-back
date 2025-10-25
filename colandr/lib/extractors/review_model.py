"""Metadata extraction from document full text."""

import logging
from collections import defaultdict
from dataclasses import dataclass
from typing import Optional

import numpy as np
import pandas as pd
from sklearn.base import BaseEstimator, TransformerMixin
from sklearn.compose import ColumnTransformer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import SGDClassifier
from sklearn.metrics import classification_report
from sklearn.multioutput import MultiOutputClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import MultiLabelBinarizer, StandardScaler
from spacy.tokens import Doc, Span

from ..nlp.utils import process_texts_into_docs
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


class VectorReshaper(BaseEstimator, TransformerMixin):
    """Transformer that reshapes a pandas Series of 1D arrays into a 2D numpy array."""

    def fit(self, x: pd.Series, y: Optional[pd.Series] = None) -> "VectorReshaper":
        """Fits the transformer (no-op)."""
        return self

    def transform(self, x: pd.Series) -> np.ndarray:
        """
        Reshape a Series of arrays into a 2D NumPy array.

        Args:
            x: A pandas Series where each element is a 1D array.

        Returns:
            A 2D NumPy array of shape (n_samples, n_features).
        """
        return np.vstack(x)


class ReviewModel:
    """
    Review-specific model for metadata extraction.

    This class builds a multi-label classification pipeline to identify key
    sentences in documents that correspond to specific metadata labels. It is
    designed to be trained on a corpus of documents with known labels.

    The model's intelligence comes from a sophisticated feature engineering
    pipeline that combines three types of features for each sentence:
    1.  **TF-IDF Features**: Based on lemmatized n-grams to capture important
        keywords and phrases.
    2.  **Sentence Embeddings**: Semantic vectors from a spaCy model that
        capture the contextual meaning of the sentence.
    3.  **Numeric Features**: Simple features like the sentence's relative
        position in the document.

    Once trained, the `extract_metadata` method can be used to process new,
    unseen documents and return the most relevant sentences for each potential label.

    Usage Example:
        # 1. Load your full dataset (list of TrainingData objects)
        all_my_data = load_my_data()

        # 2. Split into training and validation sets
        from sklearn.model_selection import train_test_split
        train_set, validation_set = train_test_split(all_my_data, test_size=0.2)

        # 3. Instantiate and train the model
        model = ReviewModel()
        model.train(training_data=train_set)

        # 4. (Optional) Validate the model and log metrics
        model.validate(validation_data=validation_set)

        # 5. Extract metadata from a new document
        new_document_text = "The study of forest management shows..."
        extracted_meta = model.extract_metadata(record_id=999, text=new_document_text)
        print(extracted_meta)
    """

    def __init__(self):
        """Initialize the model."""
        self.pipeline: Optional[Pipeline] = None
        self.label_binarizer: Optional[MultiLabelBinarizer] = None
        self.last_training_size: int = 0

    def train(self, training_data: list[TrainingData], min_samples: int = 40) -> bool:
        """
        Train a single multi-label classifier for all metadata fields.

        Args:
            training_data: List of training data records
            min_samples: The minimum number of total label instances required to train.

        Returns:
            bool: True if training was successful, False otherwise.
        """
        if not training_data:
            logger.warning("No training data provided. Model not trained.")
            return False

        total_label_count = self._count_total_labels(training_data)
        if total_label_count < min_samples:
            logger.warning(
                "Not enough training data. Found %s labels, but require %s.",
                total_label_count,
                min_samples,
            )
            return False

        try:
            x_train, targets = self._create_sentence_features(training_data)
        except ValueError as e:
            logger.error("Failed to prepare training data: %s", e)
            return False

        logger.info("Generated %s sentence examples for training.", x_train.shape[0])

        self.label_binarizer = MultiLabelBinarizer()
        y_train = self.label_binarizer.fit_transform(targets)
        logger.info("Discovered %s unique labels.", len(self.label_binarizer.classes_))

        tfidf_vectorizer = TfidfVectorizer(
            ngram_range=(1, 2), max_features=20000, min_df=3
        )
        preprocessor = ColumnTransformer(
            transformers=[
                ("tfidf", tfidf_vectorizer, "lemmatized_text"),
                ("vectors", VectorReshaper(), "sentence_vector"),
                ("numeric", StandardScaler(), ["position", "sentence_length"]),
            ],
            remainder="drop",
        )

        sgd_classifier = SGDClassifier(
            loss="log_loss",
            random_state=42,
            early_stopping=True,
            n_iter_no_change=10,
            alpha=5e-4,
            class_weight="balanced",
        )

        self.pipeline = Pipeline(
            [
                ("preprocessor", preprocessor),
                ("classifier", MultiOutputClassifier(sgd_classifier)),
            ]
        )

        logger.info("Starting model training...")
        self.pipeline.fit(x_train, y_train)

        self.last_training_size = total_label_count
        logger.info(
            "Training completed successfully with %s labels.", self.last_training_size
        )

        return True

    def validate(self, validation_data: list[TrainingData]) -> Optional[str]:
        """
        Validates the trained model against a validation dataset.

        Args:
            validation_data: List of validation data to score the model against.

        Returns:
            A string containing the classification report, or None if validation fails.
        """
        if self.pipeline is None or self.label_binarizer is None:
            logger.warning("Model has not been trained yet. Cannot validate.")
            return None

        logger.info("--- Starting Model Validation ---")
        try:
            x_val, targets_val_true = self._create_sentence_features(validation_data)
            y_val_true = self.label_binarizer.transform(targets_val_true)

            y_val_pred = self.pipeline.predict(x_val)

            report = classification_report(
                y_val_true,
                y_val_pred,
                target_names=self.label_binarizer.classes_,
                zero_division=0,
            )
            logger.info("Model Validation Report:\n%s", report)
            return report

        except Exception as e:
            logger.error("Failed during model validation: %s", e)
            return None

    def extract_metadata(
        self, record_id: int, text: str, threshold: float = 0.5
    ) -> list[Metadata]:
        """
        Extract metadata from a new text document using the trained model.

        Args:
            record_id: An identifier for the record being processed.
            text: The full text content to extract metadata from.
            threshold: The confidence threshold for returning a prediction (0.0 to 1.0).

        Returns:
            List of extracted Metadata objects, sorted by confidence.
        """
        if self.pipeline is None or self.label_binarizer is None:
            logger.warning("Model has not been trained yet. Cannot extract metadata.")
            return []

        features_df, original_sentences = self._process_text(text)
        if features_df.empty:
            return []

        x_predict = features_df
        list_of_prob_arrays = self.pipeline.predict_proba(x_predict)
        probabilities = np.hstack(
            [arr[:, 1].reshape(-1, 1) for arr in list_of_prob_arrays]
        )

        results: list[Metadata] = []
        for i, sentence_scores in enumerate(probabilities):
            for j, prob in enumerate(sentence_scores):
                if prob >= threshold:
                    label_full = self.label_binarizer.classes_[j]
                    field, value = label_full.split(":", 1)
                    results.append(
                        Metadata(
                            record=record_id,
                            metadata=field,
                            value=value,
                            sentence=original_sentences[i]["text"],
                            sentence_location=original_sentences[i]["index"],
                            confidence=prob,
                            confidence_level=self._get_confidence_level(
                                threshold, prob
                            ),
                        )
                    )

        grouped_results: dict[str, list[Metadata]] = defaultdict(list)
        for res in results:
            grouped_results[res.metadata].append(res)

        final_results = []
        for field, items in grouped_results.items():
            top_3 = sorted(items, key=lambda x: x.confidence, reverse=True)[:3]
            final_results.extend(top_3)

        return sorted(final_results, key=lambda x: x.confidence, reverse=True)

    def compare_and_train(
        self,
        training_data: list[TrainingData],
        min_samples: int = 40,
        increase_requirement: int = 5,
    ) -> tuple[bool, "ReviewModel"]:
        """
        Compare new training data with previous data and retrain if necessary.

        Args:
            training_data: New training data to compare against.
            min_samples: Minimum number of samples needed to consider training.
            increase_requirement: Number of new samples needed to trigger retraining.

        Returns:
            Tuple of (was_retrained, self).
        """
        if not training_data:
            logger.info("No training data provided for comparison.")
            return False, self

        current_total_labels = self._count_total_labels(training_data)

        if current_total_labels < min_samples:
            logger.info(
                "Current data (%s labels) is below minimum of %s. Not training.",
                current_total_labels,
                min_samples,
            )
            return False, self

        if current_total_labels >= self.last_training_size + increase_requirement:
            logger.info(
                "New data meets retraining threshold (%s >= %s + %s).",
                current_total_labels,
                self.last_training_size,
                increase_requirement,
            )
            was_trained = self.train(training_data, min_samples=min_samples)
            return was_trained, self

        logger.info(
            "Not retraining model. New data (%s labels) does not exceed threshold.",
            current_total_labels,
        )
        return False, self

    def _create_sentence_features(
        self, data: list[TrainingData]
    ) -> tuple[pd.DataFrame, list]:
        """
        Process documents and extract sentence-level features.

        Args:
            data: List of TrainingData objects.

        Returns:
            Tuple containing:
            - DataFrame where each row is a sentence with its features.
            - List of lists, containing the document-level labels for each sentence.
        """
        features_list = []
        targets_list = []

        logger.info("Preparing data from %s documents...", len(data))

        doc_labels = defaultdict(set)
        for item in data:
            for label in item.labels:
                if isinstance(label, SingleValue):
                    doc_labels[item.record_id].add(f"{label.label}:{label.value}")
                elif isinstance(label, MultiValue):
                    for value in label.values:
                        doc_labels[item.record_id].add(f"{label.label}:{value}")

        main_contents = (self._split_references(item.text_content)[0] for item in data)
        processed_docs = process_texts_into_docs(
            main_contents, max_len=None, exclude=("ner",)
        )

        for item, doc in zip(data, processed_docs):
            doc_features, _ = self._extract_features_from_doc(doc)
            if doc_features.empty:
                continue

            current_doc_labels = list(doc_labels[item.record_id])
            features_list.append(doc_features)
            targets_list.extend([current_doc_labels] * len(doc_features))

        if not features_list:
            raise ValueError(
                "No valid examples could be generated from the provided data"
            )

        return pd.concat(features_list, ignore_index=True), targets_list

    def _extract_features_from_doc(
        self, doc: Optional[Doc]
    ) -> tuple[pd.DataFrame, list[dict]]:
        """
        Extracts a feature DataFrame and sentence context from a single spaCy Doc.

        Args:
            doc: A processed spaCy Doc object, or None.

        Returns:
            Tuple containing:
            - DataFrame of features.
            - List of dictionaries containing the original sentence text and index.
        """
        if not doc:
            return pd.DataFrame(), []
        features_list = []
        original_sentences = []
        sentences = list(doc.sents)
        total_sentences = len(sentences)

        for i, sent in enumerate(sentences):
            if self._is_valid_sentence(sent):
                lemmas = [
                    tok.lemma_.lower()
                    for tok in sent
                    if tok.is_alpha and not tok.is_stop
                ]
                features_list.append(
                    {
                        "lemmatized_text": " ".join(lemmas),
                        "sentence_vector": sent.vector,
                        "position": i / total_sentences,
                        "sentence_length": len(sent),
                    }
                )
                original_sentences.append({"text": sent.text.strip(), "index": i})

        return pd.DataFrame(features_list), original_sentences

    def _process_text(self, text_content: str) -> tuple[pd.DataFrame, list[dict]]:
        """
        Processes a single raw text into a feature DataFrame and sentence context.

        Args:
            text_content: The raw text of the document.

        Returns:
            Tuple containing the feature DataFrame and original sentences list.
        """
        main_content, _ = self._split_references(text_content)
        processed_docs_iter = process_texts_into_docs(
            [main_content], max_len=None, exclude=("ner",)
        )
        doc = next(processed_docs_iter, None)

        return self._extract_features_from_doc(doc)

    def _is_valid_sentence(self, sent: Optional[Span]) -> bool:
        """
        Helper to check if a spaCy sentence span is valid for processing.

        Args:
            sent: A spaCy Span object representing a sentence.

        Returns:
            True if the sentence is valid, False otherwise.
        """
        if sent is None:
            return False
        sent_text = sent.text.strip()
        exclude_keywords = {"org.apache", "WARN", "DEBUG"}
        if len(sent_text) < 50 or any(
            keyword in sent_text for keyword in exclude_keywords
        ):
            return False
        if not any(token.pos_ == "VERB" for token in sent):
            return False
        return True

    def _split_references(self, text: str) -> tuple[str, str]:
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

    def _get_confidence_level(self, threshold: float, prob: float) -> int:
        """
        Calculate a discrete confidence level (0-2) based on probability.

        Args:
            threshold: The minimum prediction threshold.
            prob: The prediction probability for a given label.

        Returns:
            Integer confidence level from 0 to 2.
        """
        if prob < threshold:
            return 0
        one_third = (1.0 - threshold) / 3
        thresholds = [threshold + i * one_third for i in range(3)]

        return sum(prob >= t for t in thresholds) - 1

    @staticmethod
    def _count_total_labels(training_data: list[TrainingData]) -> int:
        """
        Helper function to count all individual label instances.

        Args:
            training_data: List of TrainingData

        Returns:
            Int number of labels
        """
        count = 0
        for item in training_data:
            for label in item.labels:
                if isinstance(label, SingleValue):
                    count += 1
                elif isinstance(label, MultiValue):
                    count += len(label.values)
        return count
