"""Location extraction from document full text."""

import collections
import logging

from spacy.tokens import Span
import textacy

from .metadata import Metadata


logger = logging.getLogger(__name__)


class LocationExtractor:
    """Extract locations from document text using spaCy NER."""

    def __init__(self, model: str = "en_core_web_md"):
        """Initialize the extractor with the specified language model."""
        self.nlp = textacy.load_spacy_lang(model)  # TODO: implement language detection
        # Ensure we have sentence segmentation and named entity recognition
        if not self.nlp.has_pipe("ner"):
            raise ValueError(f"Model {model} doesn't have NER component")

    def is_in_reference(self, ent: Span) -> bool:
        """
        Determine if entity is inside a reference section.

        checks if we're inside parentheses which likely indicates a citation reference.
        """
        # Check tokens before this entity for opening parenthesis
        sent = ent.sent
        start_idx = ent.start

        for i in range(start_idx - 1, sent.start - 1, -1):
            if i < 0:
                break
            token = sent.doc[i]
            if token.text == ")":
                return False
            if token.text == "(":
                return True

        return False

    def extract_locations(self, record_id: int, text: str) -> list[Metadata]:
        """
        Extract locations from text and return structured data.

        Args:
            text: The document full text

        Returns:
            List of location metadata dicts with confidence, sentences, etc.
        """
        if not text or not text.strip():
            return []

        doc = self.nlp(text)

        # Get all sentences
        sentences = list(doc.sents)
        if not sentences:
            return []

        # Extract location entities
        locations = []
        for ent in doc.ents:
            if ent.label_ in {"GPE", "LOC"} and not self.is_in_reference(ent):
                # Get context (3 sentences before and after)
                sent_idx = ent.sent.start_char
                sent_pos = -1

                for i, s in enumerate(sentences):
                    if s.start_char == sent_idx:
                        sent_pos = i
                        break

                if sent_pos == -1:
                    continue

                context_start = max(0, sent_pos - 3)
                context_end = min(len(sentences) - 1, sent_pos + 3)
                context = "\n".join(
                    sent.text for sent in sentences[context_start : context_end + 1]
                )

                locations.append(
                    {
                        "entity": ent.text,
                        "sentence": context,
                        "sentence_location": sent_pos
                    }
                )

        return self._group_locations(record_id, locations)

    def _group_locations(
        self, record_id: int, locations: list[Metadata]
    ) -> list[Metadata]:
        """
        Group locations by name and sort by frequency.

        Args:
            locations: List of extracted location dictionaries

        Returns:
            List of grouped location metadata with confidence
        """
        # Group by location name
        grouped = collections.defaultdict(list)
        for loc in locations:
            grouped[loc["entity"].lower()].append(loc)

        # Sort groups by count (most mentions first)
        result = []
        for entity, locs in sorted(
            grouped.items(), key=lambda x: len(x[1]), reverse=True
        ):
            # Sort locations by position in document
            sorted_locs = sorted(locs, key=lambda x: x["sentence_location"])

            result.append(
                Metadata(
                    record=record_id,
                    metadata="location",
                    value=entity,
                    sentence="\n".join(loc["sentence"] for loc in sorted_locs),
                    sentence_location=sorted_locs[0]["sentence_location"],
                    confidence=1.0,
                )
            )

        return result


def get_locations(record_id: int, text: str) -> list[Metadata]:
    """
    Extract locations from text using the LocationExtractor.

    Args:
        text: The document full text

    Returns:
        List of location metadata
    """
    extractor = LocationExtractor()
    return extractor.extract_locations(record_id, text)
