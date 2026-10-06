"""Tests for the fulltext locations API."""

from unittest.mock import patch

import pytest

from colandr.lib.extractors.metadata import Metadata

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

FULLTEXT_LOCATIONS_API_ENDPOINT = "fulltext_locations.fulltext_locations"
PATCH_FUNC_PATH = "colandr.api.v1.routes.fulltext_locations"

# NOTE: extractor keeps only ``LOC`` entities, not geopolitical (``GPE``) entities
FULLTEXT_TEXT = "Samples were collected near Mount Kilimanjaro."


@pytest.fixture
def graph(db_session):
    """A review with one study carrying an explicit fulltext text."""
    review = factories.create_review(db_session)
    s1 = factories.create_study(
        db_session, review=review, fulltext={"text_content": FULLTEXT_TEXT}
    )
    return {"s1": s1}


class TestFulltextLocationsAPI:
    @pytest.mark.parametrize(
        ["study_key", "status_code"],
        [
            ("s1", 200),
            (None, 404),
        ],
    )
    def test_get(self, study_key, status_code, graph, api):
        """Get locations extracted from a study's fulltext, unmocked."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.get(FULLTEXT_LOCATIONS_API_ENDPOINT, id=study_id)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert isinstance(data, list)
            for location in data:
                assert "record" in location
                assert "metadata" in location
                assert "value" in location
                assert "sentence" in location
                assert "sentence_location" in location
                assert "confidence" in location
                assert "confidence_level" in location

    @patch(f"{PATCH_FUNC_PATH}.get_locations")
    def test_get_with_mock(self, mock_get_locations, graph, api):
        """Get locations for one study, from a mocked extractor."""
        study = graph["s1"]
        mock_get_locations.return_value = [
            Metadata(
                record=study.id,
                metadata="location",
                value="kenya",
                sentence="This study was conducted in Kenya.",
                sentence_location=5,
                confidence=1.0,
            ),
            Metadata(
                record=study.id,
                metadata="location",
                value="tanzania",
                sentence="Similar studies have been conducted in Tanzania.",
                sentence_location=10,
                confidence=1.0,
            ),
        ]

        response = api.get(FULLTEXT_LOCATIONS_API_ENDPOINT, id=study.id)
        assert response.status_code == 200

        locations_data = response.json
        assert len(locations_data) == 2
        # the extracted records name the study they came from, and nothing else
        assert [loc["record"] for loc in locations_data] == [study.id, study.id]
        assert {loc["value"] for loc in locations_data} == {"kenya", "tanzania"}
        for loc in locations_data:
            assert loc["metadata"] == "location"
            for field in ("sentence", "sentence_location", "confidence"):
                assert field in loc

        # the route extracts from the study's stored text, under the study's own id
        mock_get_locations.assert_called_once_with(study.id, FULLTEXT_TEXT)
