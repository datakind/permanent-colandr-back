"""Tests for the study tags API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

STUDY_TAGS_API_ENDPOINT = "study_tags.study_tags"


@pytest.fixture
def graph(db_session):
    """Two reviews, each holding tagged studies; review 1 also holds an untagged one.

    The acting user is the world's admin, who needs no team association here.
    """
    review1, review2 = factories.create_reviews(
        db_session, n=2, names=["NAME1", "NAME2"]
    )
    factories.create_studies(
        db_session, review1, n=3, tagss=[["TAG2", "TAG1"], ["TAG1", "TAG3"], []]
    )
    factories.create_study(db_session, review2, tags=["TAG4"])
    return {"review1": review1, "review2": review2}


class TestStudyTagsAPI:
    @pytest.mark.parametrize(
        ["review_key", "status_code", "exp_tags"],
        [
            ("review1", 200, ["TAG1", "TAG2", "TAG3"]),
            ("review2", 200, ["TAG4"]),
            (None, 404, None),
        ],
    )
    def test_get(self, review_key, status_code, exp_tags, graph, api):
        """Get the distinct tags assigned to a review's studies."""
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.get(STUDY_TAGS_API_ENDPOINT, review_id=review_id)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert isinstance(data, list)
            assert data == exp_tags
