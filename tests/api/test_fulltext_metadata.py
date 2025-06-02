import flask
import pytest
from unittest.mock import patch


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
    def test_get(self, id_, params, status_code, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for("fulltext_metadata_fulltext_metadata_resource", id=id_, **params)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert isinstance(data, list)
            for metadata in data:
                assert "record" in metadata
                assert "metadata" in metadata
                assert "value" in metadata
                assert "sentence" in metadata
                assert "sentence_location" in metadata
                assert "confidence" in metadata
                assert "confidence_level" in metadata
                if params["meta"]:
                    assert metadata["metadata"] == params["meta"]

    @patch("colandr.apis.resources.fulltext_metadata.extract_metadata")
    def test_get_with_mock(self, mock_extract_metadata, app, client, admin_headers):
        """Test getting metadata with mocked extraction."""
        mock_metadata = [
            {
                "record": 1,
                "metadata": "biome",
                "value": "forest",
                "sentence": "This study was conducted in a tropical forest.",
                "sentence_location": 8,
                "confidence": 0.85,
                "confidence_level": 2
            },
            {
                "record": 1,
                "metadata": "species",
                "value": "lion",
                "sentence": "We observed several lion populations.",
                "sentence_location": 15,
                "confidence": 0.92,
                "confidence_level": 3
            }
        ]
        mock_extract_metadata.return_value = mock_metadata

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

    @patch("colandr.apis.resources.fulltext_metadata.extract_metadata")
    def test_get_filtered_with_mock(self, mock_extract_metadata, app, client, admin_headers):
        """Test getting filtered metadata with mocked extraction."""
        mock_metadata = [
            {
                "record": 1,
                "metadata": "biome",
                "value": "forest",
                "sentence": "This study was conducted in a tropical forest.",
                "sentence_location": 8,
                "confidence": 0.85,
                "confidence_level": 2
            }
        ]
        mock_extract_metadata.return_value = mock_metadata

        with app.test_request_context():
            params = {"meta": "biome"}
            url = flask.url_for("fulltext_metadata_fulltext_metadata_resource", id=1, **params)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200

        metadata_data = response.json
        assert len(metadata_data) == 1
        assert metadata_data[0]["metadata"] == "biome"

        mock_extract_metadata.assert_called_with(
            record_id=1,
            review_id=1,
            text="This is an example text in English.",
            meta="biome"
        )
