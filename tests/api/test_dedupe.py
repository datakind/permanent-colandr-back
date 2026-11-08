"""Tests for the dedupe API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

# NOTE: the blueprint is "deduplicate studies" (with a space), so that's the endpoint prefix
DEDUPE_API_ENDPOINT = "deduplicate studies.dedupe"


@pytest.fixture
def graph(db_session):
    """An active review, a frozen one, and a user on neither team.

    The acting user is the world's admin, who doesn't need a team association.
    """
    outsider = factories.create_user(db_session)
    review1 = factories.create_review(db_session)
    review2 = factories.create_review(db_session, status="frozen")
    return {"review1": review1, "review2": review2, "outsider": outsider}


class TestDedupeAPI:
    def test_post(self, graph, api, enqueued):
        """Queue a dedupe job for a review, with the route's fixed countdown."""
        review = graph["review1"]
        response = api.post(DEDUPE_API_ENDPOINT, review_id=review.id)
        assert response.status_code == 200
        assert enqueued["deduplicate_citations"] == [
            {"args": [review.id], "countdown": 3}
        ]

    @pytest.mark.parametrize(
        ["review_key", "actor", "status_code"],
        [
            ("review1", "outsider", 403),  # not on the team
            ("review2", "admin", 403),  # the admin may not dedupe a frozen review
            (None, "admin", 404),
        ],
    )
    def test_post_errors(self, review_key, actor, status_code, graph, api, enqueued):
        """Refuse a dedupe the caller can't request, and queue nothing."""
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        client = api if actor == "admin" else api.as_user(graph[actor])
        response = client.post(DEDUPE_API_ENDPOINT, review_id=review_id)
        assert response.status_code == status_code
        assert enqueued["deduplicate_citations"] == []

    @pytest.mark.parametrize(
        "params", [{}, {"review_id": 0}], ids=["missing", "too-small"]
    )
    def test_post_invalid(self, params, api):
        """Reject a missing or out-of-range review id."""
        assert api.post(DEDUPE_API_ENDPOINT, **params).status_code == 422
