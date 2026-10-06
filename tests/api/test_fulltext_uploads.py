"""Tests for the fulltext uploads API."""

import pathlib

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

FULLTEXT_UPLOAD_API_ENDPOINT = "fulltext_uploads.fulltext_upload"
FULLTEXTS_FIXTURES_DIR = pathlib.Path(__file__).parent.parent / "fixtures" / "fulltexts"

FULLTEXT_TEXT1 = "This is an example text in English. Second sentence."
FULLTEXT1_SOURCE = "example-journal-short.pdf"


def _upload_file_path(app, study) -> pathlib.Path:
    """Where the upload/get/delete routes keep a study's uploaded file.

    The routes name a study's file after its id -- ``"{id}.pdf"`` under the review's
    uploads dir -- so callers have to derive the name from the created objects.
    """
    return (
        pathlib.Path(app.config["FULLTEXT_UPLOADS_DIR"])
        / str(study.review_id)
        / f"{study.id}.pdf"
    )


@pytest.fixture
def graph(db_session, app):
    """A review with two studies: ``s1`` has an uploaded fulltext, ``s2`` has none.

    The acting user is the world's admin, who needs no team association. ``s1`` fulltext
    filename is created automatically by the factory function, derived from the study id.
    """
    review = factories.create_review(db_session)
    s1 = factories.create_study(
        db_session,
        review=review,
        fulltext={
            "original_filename": FULLTEXT1_SOURCE,
            "text_content": FULLTEXT_TEXT1,
        },
    )
    s2 = factories.create_study(db_session, review=review)
    factories.store_fulltext_file(app, s1, FULLTEXT1_SOURCE)
    return {"review": review, "s1": s1, "s2": s2}


class TestFulltextUploadAPI:
    def test_get(self, graph, api):
        """Get the uploaded file for a study's fulltext, as the world's admin."""
        response = api.get(
            FULLTEXT_UPLOAD_API_ENDPOINT,
            id=graph["s1"].id,
            review_id=graph["review"].id,
        )
        assert response.status_code == 200
        # TODO: figure out if/how we can make send_from_directory() work correctly in test
        # data = response.json
        # assert data

    @pytest.mark.parametrize(
        "file_name", ["example-journal-short.pdf", "example-journal.pdf"]
    )
    def test_post(self, file_name, graph, api, app):
        """Upload a fulltext file for a study that doesn't have one yet."""
        study = graph["s2"]
        assert not study.fulltext
        with (FULLTEXTS_FIXTURES_DIR / file_name).open(mode="rb") as f:
            response = api.post(
                FULLTEXT_UPLOAD_API_ENDPOINT,
                id=study.id,
                files={"uploaded_file": (f, file_name)},
            )
        assert response.status_code == 200
        data = response.json
        assert data
        assert data["id"] == study.id
        assert data["review_id"] == study.review_id
        assert data["filename"] == f"{study.id}.pdf"
        assert data["original_filename"] == file_name
        # the route parses the uploaded pdf into text and stores it on the study
        assert data["text_content"].strip()
        # and it puts the file where the get/delete routes will look for it
        assert _upload_file_path(app, study).is_file()

    def test_delete(self, graph, api, app):
        """Delete a study's uploaded fulltext file, emptying the study's fulltext."""
        study = graph["s1"]
        assert _upload_file_path(app, study).is_file()
        response = api.delete(FULLTEXT_UPLOAD_API_ENDPOINT, id=study.id)
        assert response.status_code == 204
        assert not _upload_file_path(app, study).exists()
