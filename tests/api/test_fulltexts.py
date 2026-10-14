"""Tests for the fulltexts API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

FULLTEXT_API_ENDPOINT = "fulltexts.fulltext"

# NOTE: fulltext names are automatically derived in-factory from the created study's id
FULLTEXT1 = {
    "original_filename": "example-journal-short.pdf",
    "text_content": "This is an example text in English. Second sentence.",
}
FULLTEXT2 = {
    "original_filename": "example-journal.pdf",
    "text_content": "This is another example text in English.",
}


@pytest.fixture
def graph(db_session, app):
    """A review with two studies, each carrying a fulltext and its uploaded file.

    The acting user is the world's admin, who needs no team association. ``fulltexts``
    holds snapshots of the dicts, not the studies' own attributes: ``create_study()``
    keeps the object it's handed, and the get endpoint merges id/review_id/... into
    ``study.fulltext`` in-place.
    """
    review = factories.create_review(db_session)
    s1, s2 = factories.create_studies(
        db_session, 2, review=review, fulltexts=[dict(FULLTEXT1), dict(FULLTEXT2)]
    )
    factories.store_fulltext_file(app, s1, FULLTEXT1["original_filename"])
    factories.store_fulltext_file(app, s2, FULLTEXT2["original_filename"])
    return {
        "review": review,
        "s1": s1,
        "s2": s2,
        "fulltexts": {"s1": dict(s1.fulltext), "s2": dict(s2.fulltext)},
    }


class TestFulltextAPI:
    @pytest.mark.parametrize(
        ["study_key", "fields", "status_code"],
        [
            ("s1", None, 200),
            ("s2", None, 200),
            ("s1", "id,review_id", 200),
            ("s1", "filename", 200),
            (None, None, 404),
        ],
    )
    def test_get(self, study_key, fields, status_code, graph, api):
        """Get a study's fulltext."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        params = {"fields": fields} if fields is not None else {}
        response = api.get(FULLTEXT_API_ENDPOINT, id=study_id, **params)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            exp_fulltext = graph["fulltexts"][study_key]
            # the requested fields, plus "id", which is always included
            exp_fields = None if fields is None else sorted({*fields.split(","), "id"})
            assert data["id"] == study_id
            # the pseudo-record names the review it belongs to; timestamps are left
            # out of the expectation, since they're written by the database
            exp_pseudo = {"review_id": graph["review"].id, **exp_fulltext}
            exp_data = {
                key: val
                for key, val in exp_pseudo.items()
                if exp_fields is None or key in exp_fields
            }
            assert {k: v for k, v in data.items() if k in exp_data} == exp_data
            if exp_fields is not None:
                assert sorted(data.keys()) == exp_fields

    @pytest.mark.parametrize("study_key", ["s1", "s2"])
    def test_delete(self, study_key, graph, api):
        """Delete a study's fulltext, emptying it out."""
        study = graph[study_key]
        response = api.delete(FULLTEXT_API_ENDPOINT, id=study.id)
        assert response.status_code == 204
        # TODO: decide on delete behavior for study.fulltext
        # get_response = client.get(url, headers=admin_headers)
        # assert get_response.status_code == 404  # not found!
        get_response = api.get(FULLTEXT_API_ENDPOINT, id=study.id)
        assert get_response.json == {}  # empty!
