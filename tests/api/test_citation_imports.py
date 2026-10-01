"""Tests for the citation imports API."""

import pathlib

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

CITATION_IMPORTS_API_ENDPOINT = "citation_imports.citation_imports"
CITATIONS_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "citations"


def _post_citation_file(
    api, review_id: int, file_name: str, *, status: str = "included"
):
    """Upload one fixture citation file to the import endpoint, as the world's admin."""
    with (CITATIONS_FIXTURES_DIR / file_name).open(mode="rb") as f:
        return api.post(
            CITATION_IMPORTS_API_ENDPOINT,
            files={"uploaded_file": (f, file_name)},
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
