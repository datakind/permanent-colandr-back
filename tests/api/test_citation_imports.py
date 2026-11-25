"""Tests for the citation imports API."""

import io
import pathlib

import pytest

from colandr.api.v1 import schemas
from colandr.api.v1.routes.citation_imports import _preprocess_citations

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

CITATION_IMPORTS_API_ENDPOINT = "citation_imports.citation_imports"
CITATION_API_ENDPOINT = "citations.citation"
STUDIES_API_ENDPOINT = "studies.studies"
CITATIONS_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "citations"

# prod bug case: a record whose "ID" tag holds a non-numeric, non-Colandr identifier
RIS_WITH_SOURCE_ID = b"""\
TY  - JOUR
ID  - REF-2024-001
TI  - Test Title
AB  - Test abstract.
AU  - DeWilde, B.
PY  - 2026
ER  -
"""


def _post_citation_file(
    api, review_id: int, file_name: str, *, status: str = "included"
):
    """Upload one fixture citation file to the import endpoint, as the world's admin."""
    content = (CITATIONS_FIXTURES_DIR / file_name).read_bytes()
    return _post_citations(api, review_id, content, file_name, status=status)


def _post_citations(
    api, review_id: int, content: bytes, file_name: str, *, status: str = "included"
):
    """Upload citation file content to the import endpoint, as the world's admin."""
    return api.post(
        CITATION_IMPORTS_API_ENDPOINT,
        files={"uploaded_file": (io.BytesIO(content), file_name)},
        review_id=review_id,
        status=status,
        source_type="database",
    )


@pytest.fixture
def graph(db_session, admin_user):
    """A review owned by the world's admin, with no imports of its own yet."""
    review = factories.create_review_with_team(
        db_session, owner=admin_user, name="NAME1"
    )
    return {"review": review}


class TestCitationsImportsResource:
    @pytest.mark.parametrize("file_name", ["example.ris", "example.bib"])
    def test_post(self, file_name, graph, api):
        """Import citations from an uploaded file."""
        response = _post_citation_file(api, graph["review"].id, file_name)
        assert response.status_code == 200

    def test_get(self, graph, api):
        """Get a review's citation import history, after importing two files.

        The two imports have to be made here rather than in a ``test_post``,
        since every test runs in its own rolled-back transaction.
        """
        review = graph["review"]
        for file_name in ["example.ris", "example.bib"]:
            assert _post_citation_file(api, review.id, file_name).status_code == 200

        response = api.get(CITATION_IMPORTS_API_ENDPOINT, review_id=review.id)
        assert response.status_code == 200
        data = response.json
        assert data
        assert isinstance(data, list) and len(data) == 2
        assert {record["review_id"] for record in data} == {review.id}
        assert {record["record_type"] for record in data} == {"citation"}
        assert {record["status"] for record in data} == {"included"}
        # the endpoint's own parser reads four citations out of each fixture file
        assert sorted(record["num_records"] for record in data) == [4, 4]


class TestPreprocessCitations:
    def test_source_record_id_included_as_other_field(self, app):
        """A source record "ID" must land in ``other_fields``, not at the top level."""
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(RIS_WITH_SOURCE_ID), "test.ris"
            )

        assert len(citations) == 1
        citation = citations[0]
        assert "id" not in citation
        assert citation["other_fields"] == {"id": "REF-2024-001"}
        assert citation["title"] == "Test Title"
        assert citation["pub_year"] == 2026
        assert citation["authors"] == ["DeWilde, B."]

    def test_output_matches_stored_citation_shape(self, app):
        """Only ``StudyCitationSchema`` fields may appear at the top level."""
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(RIS_WITH_SOURCE_ID), "test.ris"
            )

        citation = citations[0]
        assert set(citation) <= set(schemas.StudyCitationSchema().fields)
        assert schemas.StudyCitationSchema().dump(citation) == citation

    def test_invalid_record_is_skipped_valid_one_kept(self, app):
        """A record that fails validation is dropped; only valid records are returned."""
        too_long_title = b"TY  - JOUR\nTI  - " + b"X" * 301 + b"\nER  -\n"
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(RIS_WITH_SOURCE_ID + too_long_title), "test.ris"
            )

        assert len(citations) == 1
        assert citations[0]["title"] == "Test Title"

    def test_unparseable_content_yields_no_citations(self, app):
        """Garbage content parses to zero records rather than raising an error."""
        with app.app_context():
            citations = _preprocess_citations(
                io.BytesIO(b"not valid ris content!!!"), "test.ris"
            )

        assert citations == []


class TestCitationImportRoundTrip:
    def test_source_id_does_not_break_study_serialization(self, graph, api):
        """Import a record whose "ID" is non-numeric, then read the study back."""
        review = graph["review"]
        response = _post_citations(api, review.id, RIS_WITH_SOURCE_ID, "record-id.ris")
        assert response.status_code == 200

        # this is what the citation screenings page loads
        response = api.get(STUDIES_API_ENDPOINT, review_id=review.id)
        assert response.status_code == 200
        (obs_study,) = response.json
        citation = obs_study["citation"]
        assert citation["title"] == "Test Title"
        assert citation["pub_year"] == 2026
        assert citation["authors"] == ["DeWilde, B."]
        assert citation["other_fields"] == {"id": "REF-2024-001"}
        # study-level fields stay at the study level
        assert citation.keys().isdisjoint({"id", "review_id"})
        assert obs_study["review_id"] == review.id
        assert obs_study["citation_status"] == "included"

        # the single-citation endpoint still reports the study's id, not the source's
        response = api.get(CITATION_API_ENDPOINT, id=obs_study["id"])
        assert response.status_code == 200
        assert response.json["id"] == obs_study["id"]
        assert response.json["review_id"] == review.id

    def test_legacy_citation_blob_still_renders(self, graph, db_session, api):
        """A row imported before the schema fix keeps rendering instead of erroring."""
        review = graph["review"]
        study = factories.create_study(
            db_session,
            review=review,
            citation={
                "type_of_reference": "journal",
                "review_id": review.id,
                "id": "REF-2024-001",
                "title": "Test Title",
                "abstract": "Test abstract.",
                "authors": ["DeWilde, B."],
                "pub_year": 2026,
            },
            fulltext={
                "filename": "1.pdf",
                "original_filename": "test.pdf",
                "text_content": "Test fulltext.",
            },
        )

        response = api.get(STUDIES_API_ENDPOINT, review_id=review.id)
        assert response.status_code == 200
        (obs_study,) = response.json
        assert obs_study["id"] == study.id
        assert obs_study["citation"]["title"] == "Test Title"
        assert "id" not in obs_study["citation"]
        assert set(obs_study["fulltext"]) == {
            "filename",
            "original_filename",
            "text_content",
        }
