import io

import flask
import pytest

from colandr.api.v1.routes.citation_imports import _preprocess_citations


CITATION_IMPORTS_API_ENDPOINT = "citation_imports.citation_imports"

# Minimal valid RIS with a string ID field (the concrete production failure case)
_RIS_WITH_STRING_ID = b"""\
TY  - JOUR
ID  - REF-2024-001
TI  - Test Title
AB  - Test abstract.
AU  - DeWilde, B.
PY  - 2026
ER  -
"""

_RIS_MINIMAL = b"""\
TY  - JOUR
TI  - Minimal Title
ER  -
"""


@pytest.mark.usefixtures("db_session")
class TestCitationsImportsResource:
    @pytest.mark.parametrize(
        ["params", "file_name"],
        [
            (
                {
                    "review_id": 1,
                    "status": "included",
                    "source_type": "database",
                },
                "example.ris",
            ),
            (
                {
                    "review_id": 1,
                    "status": "included",
                    "source_type": "database",
                },
                "example.bib",
            ),
        ],
    )
    def test_post(
        self, params, file_name, app, client, db_session, admin_headers, request
    ):
        with app.test_request_context():
            url = flask.url_for(CITATION_IMPORTS_API_ENDPOINT, **(params or {}))
        dir_path = request.config.rootpath
        file_path = dir_path / "tests" / "fixtures" / "citations" / file_name
        files = {"uploaded_file": (open(file_path, mode="rb"), file_path)}
        response = client.post(url, data=files, headers=admin_headers)
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"review_id": 1}, 2),
        ],
    )
    def test_get(self, params, num_exp, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(CITATION_IMPORTS_API_ENDPOINT, **(params or {}))
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert isinstance(data, list) and len(data) == num_exp


class TestPreprocessCitations:
    def test_string_id_goes_to_other_fields_not_top_level(self, app):
        """String `id` from source file must not surface as a top-level key.

        If it does, CitationSchema.id (Integer) will raise a ValidationError
        on dump — an actual production failure that we've experienced.
        """
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(_RIS_WITH_STRING_ID), "test.ris", review_id=1
            )
        assert len(citations) == 1
        citation = citations[0]
        assert "id" not in citation
        assert "REF-2024-001" in citation.get("other_fields", {}).values()

    def test_review_id_not_stored_in_citation_json(self, app):
        """review_id belongs on the Study row, not embedded in citation JSON."""
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(_RIS_MINIMAL), "test.ris", review_id=42
            )
        assert len(citations) == 1
        assert "review_id" not in citations[0]

    def test_known_content_fields_are_present(self, app):
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(_RIS_WITH_STRING_ID), "test.ris", review_id=1
            )
        assert len(citations) == 1
        citation = citations[0]
        assert citation["title"] == "Test Title"
        assert citation["abstract"] == "Test abstract."
        assert citation["pub_year"] == 2026

    def test_unparseable_file_raises_value_error(self, app):
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(b"not valid ris content!!!"), "bad.ris", review_id=1
            )
        assert not citations
