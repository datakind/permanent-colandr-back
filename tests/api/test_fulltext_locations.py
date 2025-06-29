from unittest.mock import patch

import flask
import pytest

from colandr.lib.extractors.metadata import Metadata


@pytest.mark.usefixtures("db_session")
class TestFulltextLocationsResource:
    @pytest.mark.parametrize(
        ["id_", "status_code"],
        [
            (1, 200),
            (999, 404),
        ],
    )
    def test_get(self, id_, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "fulltext_locations_fulltext_locations_resource", id=id_
            )
        response = client.get(url, headers=admin_headers)
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

    @patch("colandr.apis.resources.fulltext_locations.get_locations")
    def test_get_with_mock(self, mock_get_locations, app, client, admin_headers):
        """Test getting locations with mocked extraction."""
        mock_locations = [
            Metadata(
                record=1,
                metadata="location",
                value="kenya",
                sentence="This study was conducted in Kenya.",
                sentence_location=5,
                confidence=1.0,
            ),
            Metadata(
                record=1,
                metadata="location",
                value="tanzania",
                sentence="Similar studies have been conducted in Tanzania.",
                sentence_location=10,
                confidence=1.0,
            ),
        ]
        mock_get_locations.return_value = mock_locations

        with app.test_request_context():
            url = flask.url_for("fulltext_locations_fulltext_locations_resource", id=1)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200

        locations_data = response.json
        assert len(locations_data) == 2

        assert locations_data[0]["record"] == 1
        assert locations_data[0]["metadata"] == "location"
        assert "value" in locations_data[0]
        assert "sentence" in locations_data[0]
        assert "sentence_location" in locations_data[0]
        assert "confidence" in locations_data[0]
