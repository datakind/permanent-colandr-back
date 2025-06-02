"""Tests for the text locations extractors."""
from unittest.mock import patch, MagicMock

from colandr.lib.extractors.locations import LocationExtractor
from colandr.lib.extractors.metadata import Metadata


class TestLocationExtractor:
    """Tests for the LocationExtractor class."""

    def test_init(self):
        """Test LocationExtractor initialization."""
        with patch("spacy.load") as mock_load:
            mock_nlp = MagicMock()
            mock_nlp.has_pipe.return_value = True
            mock_load.return_value = mock_nlp

            extractor = LocationExtractor()
            mock_load.assert_called_once_with("en_core_web_md")
            assert extractor.nlp == mock_nlp

    def test_is_in_reference(self):
        """Test is_in_reference function."""
        with patch("spacy.load") as mock_load:
            mock_nlp = MagicMock()
            mock_nlp.has_pipe.return_value = True
            mock_load.return_value = mock_nlp

            extractor = LocationExtractor()

            mock_ent = MagicMock()
            mock_sent = MagicMock()
            mock_doc = MagicMock()

            mock_ent.sent = mock_sent
            mock_ent.start = 5
            mock_sent.start = 0
            mock_sent.doc = mock_doc

            # Case 1: Parenthesis before entity
            token_paren = MagicMock()
            token_paren.text = "("
            mock_doc.__getitem__.return_value = token_paren

            assert extractor.is_in_reference(mock_ent) is True

            # Case 2: Closing parenthesis before entity
            token_close = MagicMock()
            token_close.text = ")"
            mock_doc.__getitem__.return_value = token_close

            assert extractor.is_in_reference(mock_ent) is False

            # Case 3: No parenthesis
            token_other = MagicMock()
            token_other.text = "text"
            mock_doc.__getitem__.return_value = token_other

            assert extractor.is_in_reference(mock_ent) is False

    def test_extract_locations(self):
        """Test extract_locations function."""
        with patch("spacy.load") as mock_load:
            mock_nlp = MagicMock()
            mock_nlp.has_pipe.return_value = True
            mock_load.return_value = mock_nlp

            extractor = LocationExtractor()

            mock_doc = MagicMock()
            mock_sent1 = MagicMock()
            mock_sent1.text = "This is sentence 1."
            mock_sent1.start_char = 0

            mock_sent2 = MagicMock()
            mock_sent2.text = "London is a city in England."
            mock_sent2.start_char = 20

            mock_sent3 = MagicMock()
            mock_sent3.text = "This is sentence 3."
            mock_sent3.start_char = 50

            mock_doc.sents = [mock_sent1, mock_sent2, mock_sent3]

            mock_ent1 = MagicMock()
            mock_ent1.text = "London"
            mock_ent1.label_ = "GPE"
            mock_ent1.sent = mock_sent2

            mock_ent2 = MagicMock()
            mock_ent2.text = "England"
            mock_ent2.label_ = "GPE"
            mock_ent2.sent = mock_sent2

            mock_doc.ents = [mock_ent1, mock_ent2]

            mock_nlp.return_value = mock_doc

            extractor.is_in_reference = MagicMock(return_value=False)

            with patch.object(extractor, '_group_locations') as mock_group:
                mock_group.return_value = [
                    Metadata(
                        record=1,
                        metadata="location",
                        value="london",
                        sentence="London is a city in England.",
                        sentence_location=1,
                        confidence=1.0,
                    ),
                    Metadata(
                        record=1,
                        metadata="location",
                        value="england",
                        sentence="London is a city in England.",
                        sentence_location=1,
                        confidence=1.0,
                    ),
                ]

                result = extractor.extract_locations(1, "Document with locations: London, England.")

                assert len(result) == 2
                assert result[0].value == "london"
                assert result[1].value == "england"

    def test_group_locations(self):
        """Test _group_locations function."""
        with patch("spacy.load") as mock_load:
            mock_nlp = MagicMock()
            mock_nlp.has_pipe.return_value = True
            mock_load.return_value = mock_nlp

            extractor = LocationExtractor()

            locations = [
                {
                    "entity": "London",
                    "sentence": "Sentence 1 about London.",
                    "sentence_location": 1,
                    "percentage": 0.1
                },
                {
                    "entity": "london",
                    "sentence": "Sentence 2 about london.",
                    "sentence_location": 2,
                    "percentage": 0.2
                },
                {
                    "entity": "Paris",
                    "sentence": "Sentence about Paris.",
                    "sentence_location": 3,
                    "percentage": 0.3
                }
            ]

            result = extractor._group_locations(1, locations)

            # Should group "London" and "london" together
            assert len(result) == 2

            # Check that locations are sorted by frequency (london has 2 mentions)
            assert result[0].value.lower() == "london"
            assert result[1].value.lower() == "paris"

            assert result[0].confidence == 1.0
