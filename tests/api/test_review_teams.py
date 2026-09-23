"""Tests for the review team API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

REVIEW_TEAM_API_ENDPOINT = "review_teams.review_team"
NOT_FOUND_ID = 999_999


@pytest.fixture
def graph(db_session):
    """An owner, two members, an outsider, and their two reviews.

    Neither review knows about the outsider, so it's the target of both the "add" action
    and the not-found branch of "set_role". The acting user is the admin, who's not on
    either team.
    """
    owner = factories.create_user(db_session, name="Owner")
    member1 = factories.create_user(db_session, name="Member1")
    member2 = factories.create_user(db_session, name="Member2")
    outsider = factories.create_user(db_session, name="Outsider")
    review1, review2 = factories.create_reviews(db_session, n=2)
    teams = {
        "review1": [(owner, "owner"), (member1, "member"), (member2, "member")],
        "review2": [(owner, "owner"), (member2, "member")],
    }
    for review_key, review in [("review1", review1), ("review2", review2)]:
        for user, role in teams[review_key]:
            factories.add_review_user(db_session, review, user, role=role)
    return {
        "owner": owner,
        "member1": member1,
        "member2": member2,
        "outsider": outsider,
        "review1": review1,
        "review2": review2,
        "teams": teams,
    }


class TestReviewTeamAPI:
    @pytest.mark.parametrize(
        ["review_key", "fields", "status_code"],
        [
            ("review1", None, 200),
            ("review2", None, 200),
            ("review1", "id,name", 200),
            ("review1", "name", 200),
            (None, None, 404),
        ],
    )
    def test_get(self, review_key, fields, status_code, graph, api):
        review_id = NOT_FOUND_ID if review_key is None else graph[review_key].id
        params = {"fields": fields} if fields is not None else {}
        response = api.get(REVIEW_TEAM_API_ENDPOINT, id=review_id, **params)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            exp_is_owners = {
                user.id: role == "owner" for user, role in graph["teams"][review_key]
            }
            assert sorted(record["id"] for record in data) == sorted(exp_is_owners)
            assert {
                record["id"]: record["is_owner"] for record in data
            } == exp_is_owners
            exp_fields = None
            if fields is not None:
                exp_fields = sorted({*fields.split(","), "id", "is_owner"})
            assert all("id" in record for record in data)
            if exp_fields:
                assert all(sorted(record.keys()) == exp_fields for record in data)

    @pytest.mark.parametrize(
        ["review_key", "params", "status_code"],
        [
            ("review1", {"action": "make_owner", "user_id": "member1"}, 200),
            (
                "review1",
                {"action": "set_role", "user_id": "member1", "user_role": "owner"},
                200,
            ),
            (
                "review1",
                {"action": "set_role", "user_id": "member2", "user_role": "member"},
                200,
            ),
            (
                "review1",
                {"action": "set_role", "user_id": "outsider", "user_role": "member"},
                404,
            ),
            ("review1", {"action": "remove", "user_id": "member1"}, 200),
            ("review1", {"action": "add", "user_id": "outsider"}, 200),
        ],
    )
    def test_put(self, review_key, params, status_code, graph, api):
        """Add, remove, or change the role of a user on a review team."""
        review = graph[review_key]
        user_id = graph[params["user_id"]].id
        response = api.put(
            REVIEW_TEAM_API_ENDPOINT, id=review.id, **{**params, "user_id": user_id}
        )
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            modified_users = [record for record in data if record["id"] == user_id]
            if params["action"] == "make_owner":
                assert modified_users[0]["is_owner"] is True
            elif params["action"] == "set_role":
                assert modified_users[0]["is_owner"] is (params["user_role"] == "owner")
            elif params["action"] == "remove":
                assert not modified_users
            elif params["action"] == "add":
                assert modified_users[0]["is_owner"] is False

    def test_put_as_owner(self, graph, api):
        """Modify a review team, as a non-admin owner of the review."""
        review = graph["review1"]
        response = api.as_user(graph["owner"]).put(
            REVIEW_TEAM_API_ENDPOINT,
            id=review.id,
            action="make_owner",
            user_id=graph["member1"].id,
        )
        assert response.status_code == 200
        modified_user = [
            record for record in response.json if record["id"] == graph["member1"].id
        ][0]
        assert modified_user["is_owner"] is True

    @pytest.mark.parametrize(
        "actor",
        ["member1", "outsider"],
        ids=["team-member", "not-on-team"],
    )
    def test_put_forbidden(self, actor, graph, api):
        """Modify a review team, as a non-admin who doesn't own the review."""
        response = api.as_user(graph[actor]).put(
            REVIEW_TEAM_API_ENDPOINT,
            id=graph["review1"].id,
            action="remove",
            user_id=graph["member1"].id,
        )
        assert response.status_code == 403
