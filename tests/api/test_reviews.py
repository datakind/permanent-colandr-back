"""Tests for the review(s) API."""

import flask
import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

REVIEW_API_ENDPOINT = "reviews.review"
REVIEWS_API_ENDPOINT = "reviews.reviews"


def _review_url(client, review_id: int) -> str:
    """Build a review endpoint url, outside of any request context."""
    with client.application.test_request_context():
        return flask.url_for(REVIEW_API_ENDPOINT, id=review_id)


@pytest.fixture
def graph(db_session, admin_user):
    """The world's admin, a non-admin owner, a member, and their two reviews.

    Admin and non-admin owner own review 1; the non-admin owner also owns review 2,
    while the member belongs to review 1 only.
    """
    owner, member = factories.create_users(db_session, n=2)
    review1 = factories.create_review(
        db_session, name="NAME1", description="DESCRIPTION1"
    )
    review2 = factories.create_review(
        db_session,
        name="NAME2",
        description="DESCRIPTION2",
        citation_reviewer_num_pcts=[{"num": 1, "pct": 75}, {"num": 2, "pct": 25}],
        fulltext_reviewer_num_pcts=[{"num": 2, "pct": 100}],
    )
    factories.add_review_user(db_session, review1, admin_user, role="owner")
    factories.add_review_user(db_session, review1, owner, role="owner")
    factories.add_review_user(db_session, review1, member, role="member")
    factories.add_review_user(db_session, review2, owner, role="owner")
    return {
        "admin": admin_user,
        "owner": owner,
        "member": member,
        "review1": review1,
        "review2": review2,
    }


class TestReviewAPI:
    ## GET ##

    @pytest.mark.parametrize(
        ["actor", "review_key", "fields", "exp_data"],
        [
            (
                "admin",
                "review1",
                None,
                {"name": "NAME1", "description": "DESCRIPTION1"},
            ),
            (
                "admin",
                "review2",
                None,
                {
                    "name": "NAME2",
                    "description": "DESCRIPTION2",
                    "num_citation_screening_reviewers": 1,
                    "num_fulltext_screening_reviewers": 2,
                },
            ),
            (
                "owner",
                "review2",
                None,
                {"name": "NAME2", "description": "DESCRIPTION2"},
            ),
            (
                "member",
                "review1",
                None,
                {"name": "NAME1", "description": "DESCRIPTION1"},
            ),
            ("admin", "review1", "id,name", {"name": "NAME1"}),
            ("member", "review1", "id,name", {"name": "NAME1"}),
            ("admin", "review2", "description", {"description": "DESCRIPTION2"}),
        ],
    )
    def test_get(self, actor, review_key, fields, exp_data, graph, api):
        """Get a review, as an owner/member of its team or as an admin."""
        review = graph[review_key]
        params = {"fields": fields} if fields is not None else {}
        response = api.as_user(graph[actor]).get(
            REVIEW_API_ENDPOINT, id=review.id, **params
        )
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == review.id
        assert {k: v for k, v in data.items() if k in exp_data} == exp_data

    @pytest.mark.parametrize(
        ["actor", "review_key", "status_code"],
        [
            ("admin", None, 404),
            ("member", "review2", 403),
        ],
    )
    def test_get_errors(self, actor, review_key, status_code, graph, api):
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.as_user(graph[actor]).get(REVIEW_API_ENDPOINT, id=review_id)
        assert response.status_code == status_code

    ## PUT ##

    @pytest.mark.parametrize(
        ["actor", "review_key", "data"],
        [
            ("admin", "review1", {"name": "NEW_REVIEW_NAME1"}),
            ("owner", "review1", {"description": "NEW_DESCRIPTION1"}),
            (
                "admin",
                "review2",
                {"name": "NEW_REVIEW_NAME2", "description": "NEW_DESCRIPTION2"},
            ),
            ("admin", "review2", {"num_citation_screening_reviewers": 2}),
            ("admin", "review2", {"num_fulltext_screening_reviewers": 3}),
        ],
    )
    def test_put(self, actor, review_key, data, graph, api):
        """Modify a review, as an owner of its team."""
        review = graph[review_key]
        response = api.as_user(graph[actor]).put(
            REVIEW_API_ENDPOINT, id=review.id, json=data
        )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == review.id
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["actor", "review_key", "data", "status_code"],
        [
            ("member", "review1", {"name": "NEW_NAME1"}, 403),
            ("admin", None, {"name": "NEW_NAME999"}, 404),
        ],
    )
    def test_put_errors(self, actor, review_key, data, status_code, graph, api):
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.as_user(graph[actor]).put(
            REVIEW_API_ENDPOINT, id=review_id, json=data
        )
        assert response.status_code == status_code

    ## DELETE ##

    @pytest.mark.parametrize(
        ["actor", "review_key"],
        [
            ("admin", "review1"),
            ("owner", "review2"),
        ],
    )
    def test_delete(self, actor, review_key, graph, api, client, admin_headers):
        review = graph[review_key]
        del_response = api.as_user(graph[actor]).delete(
            REVIEW_API_ENDPOINT, id=review.id
        )
        assert del_response.status_code == 204
        # verify with raw fixtures: `api` is still in user mode
        assert (
            client.get(
                _review_url(client, review.id), headers=admin_headers
            ).status_code
            == 404
        )  # not found!

    @pytest.mark.parametrize(
        ["actor", "review_key", "status_code"],
        [
            ("admin", None, 404),  # only existing reviews can be deleted
            ("member", "review1", 403),  # only admins and owners can delete reviews
        ],
    )
    def test_delete_errors(self, actor, review_key, status_code, graph, api):
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.as_user(graph[actor]).delete(REVIEW_API_ENDPOINT, id=review_id)
        assert response.status_code == status_code

    ## POST ##

    @pytest.mark.parametrize(
        "data",
        [
            {"name": "NAMEX"},
            {"name": "NAMEX", "description": "DESCX"},
            {
                "name": "NAMEX",
                "num_citation_screening_reviewers": 2,
                "num_fulltext_screening_reviewers": 2,
            },
        ],
    )
    def test_post(self, data, api):
        """Create a review."""
        response = api.post(REVIEWS_API_ENDPOINT, json=data)
        assert response.status_code == 200
        obs_data = response.json
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        "data",
        [
            {"name": None, "description": "DESCX"},
            {"name": "NAMEX", "foo": "bar"},
        ],
    )
    @pytest.mark.parametrize("actor", ["admin", "member"])
    def test_post_errors(self, actor, data, graph, api):
        """Post an invalid review record."""
        response = api.as_user(graph[actor]).post(REVIEWS_API_ENDPOINT, json=data)
        assert response.status_code == 422
