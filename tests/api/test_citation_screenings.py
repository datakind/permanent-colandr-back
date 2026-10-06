"""Tests for the citation screenings API."""

import typing as t

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

CITATION_SCREENING_API_ENDPOINT = "citation_screenings.citation_screening"
CITATION_SCREENINGS_API_ENDPOINT = "citation_screenings.citation_screenings"


def _with_ids(graph: dict[str, t.Any], record: dict[str, t.Any]) -> dict[str, t.Any]:
    """Resolve expectations that name an object in ``graph`` to that object's id.

    Keys ending in ``_id`` name a graph entry -- e.g. ``{"user_id": "reviewer1"}``
    becomes ``{"user_id": <reviewer1's id>}`` -- while every other value (statuses,
    reasons, counts, ...) is a literal and passes through untouched.
    """
    return {
        key: graph[value].id if key.endswith("_id") else value
        for key, value in record.items()
    }


@pytest.fixture
def graph(db_session, admin_user):
    """An admin-owned review with three studies and their citation screenings.

    reviewer1 screened all three -- s1 and s2 included, s3 excluded -- so s1 holds one
    screening and s2 holds two (reviewer2 screened s2 as well); s3's sole screening is
    an exclusion. The outsider belongs to no review, so every 403 targets it.
    """
    reviewer1, reviewer2, outsider = factories.create_users(
        db_session, n=3, names=["Reviewer1", "Reviewer2", "Outsider"]
    )
    review, studies = factories.create_screened_review(
        db_session,
        owner=admin_user,
        studies={
            "s1": {"num_citation_reviewers": 1},
            "s2": {"num_citation_reviewers": 1},
            "s3": {"num_citation_reviewers": 1},
        },
        screening_reviewer=reviewer1,
        decisions=[
            ("s1", None, "citation", "included", None),
            ("s2", None, "citation", "included", None),
            ("s2", reviewer2, "citation", "included", None),
            ("s3", None, "citation", "excluded", ["REASON1"]),
        ],
    )
    factories.add_review_user(db_session, review, reviewer1, role="member")
    factories.add_review_user(db_session, review, reviewer2, role="member")
    return {
        "admin": admin_user,
        "reviewer1": reviewer1,
        "reviewer2": reviewer2,
        "outsider": outsider,
        "review": review,
        **studies,
    }


class TestCitationScreeningAPI:
    @pytest.mark.parametrize(
        ["actor", "study_key", "fields", "exp_data"],
        [
            # one screening, read by the admin
            (
                "admin",
                "s1",
                None,
                [
                    {
                        "user_id": "reviewer1",
                        "review_id": "review",
                        "citation_id": "s1",
                        "status": "included",
                    }
                ],
            ),
            # two screenings, read by one of their reviewers
            (
                "reviewer1",
                "s2",
                None,
                [
                    {
                        "user_id": "reviewer1",
                        "review_id": "review",
                        "citation_id": "s2",
                        "status": "included",
                    },
                    {
                        "user_id": "reviewer2",
                        "review_id": "review",
                        "citation_id": "s2",
                        "status": "included",
                    },
                ],
            ),
            # one screening by someone else, with a field projection
            (
                "reviewer2",
                "s3",
                "id,review_id,citation_id",
                [{"review_id": "review", "citation_id": "s3"}],
            ),
        ],
    )
    def test_get(self, actor, study_key, fields, exp_data, graph, api):
        """Get a study's citation screenings."""
        study = graph[study_key]
        params = {"fields": fields} if fields is not None else {}
        response = api.as_user(graph[actor]).get(
            CITATION_SCREENING_API_ENDPOINT, id=study.id, **params
        )
        assert response.status_code == 200
        data = response.json
        assert isinstance(data, list)
        assert len(data) == len(exp_data)
        for item, exp_item in zip(data, exp_data):
            assert "id" in item
            exp = _with_ids(graph, exp_item)
            assert {k: v for k, v in item.items() if k in exp} == exp

    @pytest.mark.parametrize(
        ["actor", "study_key", "status_code"],
        [
            ("admin", None, 404),
            ("outsider", "s1", 403),
        ],
    )
    def test_get_errors(self, actor, study_key, status_code, graph, api):
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.as_user(graph[actor]).get(
            CITATION_SCREENING_API_ENDPOINT, id=study_id
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["actor", "study_key", "data"],
        [
            # admin modifies another reviewer's screening, naming them explicitly
            ("admin", "s3", {"user_id": "reviewer1", "status": "included"}),
            # a reviewer modifies their own screening, adding exclusion reasons
            (
                "reviewer1",
                "s1",
                {
                    "user_id": "reviewer1",
                    "status": "excluded",
                    "exclude_reasons": ["REASON3"],
                },
            ),
        ],
    )
    def test_put(self, actor, study_key, data, graph, api):
        """Modify a citation screening."""
        study = graph[study_key]
        data = _with_ids(graph, data)
        response = api.as_user(graph[actor]).put(
            CITATION_SCREENING_API_ENDPOINT, id=study.id, json=data
        )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data
        assert {k: v for k, v in obs_data.items() if k in data} == data
        fetched = api.get(CITATION_SCREENING_API_ENDPOINT, id=study.id).json
        row = [item for item in fetched if item["user_id"] == data["user_id"]][0]
        assert {k: v for k, v in row.items() if k in data} == data

    @pytest.mark.parametrize(
        ["actor", "study_key", "data", "status_code"],
        [
            # status is required
            ("admin", "s1", {"user_id": "reviewer1"}, 422),
            # an exclusion must come with at least one reason
            (
                "admin",
                "s1",
                {"user_id": "reviewer1", "status": "excluded"},
                400,
            ),
            ("admin", None, {"user_id": "admin", "status": "included"}, 404),
        ],
    )
    def test_put_errors(self, actor, study_key, data, status_code, graph, api):
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.as_user(graph[actor]).put(
            CITATION_SCREENING_API_ENDPOINT, id=study_id, json=_with_ids(graph, data)
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["actor", "study_key"],
        [
            ("reviewer1", "s1"),  # the study's only screening
            ("reviewer2", "s2"),  # one of the study's two screenings
        ],
    )
    def test_delete(self, actor, study_key, graph, api):
        """Delete a reviewer's own citation screening."""
        reviewer = graph[actor]
        study = graph[study_key]
        response = api.as_user(reviewer).delete(
            CITATION_SCREENING_API_ENDPOINT, id=study.id
        )
        assert response.status_code == 204
        remaining = api.get(CITATION_SCREENING_API_ENDPOINT, id=study.id).json
        assert isinstance(remaining, list)  # a study with no screenings reads as []
        assert not any(item["user_id"] == reviewer.id for item in remaining)

    @pytest.mark.parametrize(
        ["actor", "study_key", "status_code"],
        [
            ("admin", None, 404),  # only existing screenings can be deleted
            ("outsider", "s1", 403),  # only reviewers can delete their own screenings
        ],
    )
    def test_delete_errors(self, actor, study_key, status_code, graph, api):
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.as_user(graph[actor]).delete(
            CITATION_SCREENING_API_ENDPOINT, id=study_id
        )
        assert response.status_code == status_code

    @pytest.mark.parametrize(
        ["study_key", "data", "status_code"],
        [
            (
                "s1",
                {
                    "user_id": "reviewer2",
                    "review_id": "review",
                    "status": "included",
                },
                200,
            ),
            (
                "s3",
                {
                    "user_id": "reviewer2",
                    "status": "excluded",
                    "exclude_reasons": ["REASON3"],
                },
                200,
            ),
            (None, {"status": "included"}, 404),
        ],
    )
    def test_post(self, study_key, data, status_code, graph, api):
        """Create a citation screening, as an admin naming the screening reviewer."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        json_data = _with_ids(graph, data)
        response = api.post(
            CITATION_SCREENING_API_ENDPOINT, id=study_id, json=json_data
        )
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            obs_data = response.json
            assert {k: v for k, v in obs_data.items() if k in json_data} == json_data


class TestCitationScreeningsResource:
    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"citation_id": "s1"}, 1),
            ({"user_id": "reviewer1"}, 3),
            ({"review_id": "review"}, 4),
            ({"review_id": "review", "user_id": "reviewer2"}, 1),
        ],
    )
    def test_get(self, params, num_exp, graph, api):
        """Get citation screenings by citation, user, and/or review id."""
        response = api.get(CITATION_SCREENINGS_API_ENDPOINT, **_with_ids(graph, params))
        assert response.status_code == 200
        response_data = response.json
        assert isinstance(response_data, list)
        assert len(response_data) == num_exp

    @pytest.mark.parametrize(
        ["params", "exp_data"],
        [
            ({"review_id": "review"}, {"included": 3, "excluded": 1}),
            ({"user_id": "reviewer1"}, {"included": 2, "excluded": 1}),
            ({"user_id": "reviewer2"}, {"included": 1}),
            ({"review_id": "review", "user_id": "reviewer2"}, {"included": 1}),
        ],
    )
    def test_get_status_counts(self, params, exp_data, graph, api):
        """Get counts of citation screenings, grouped by status."""
        response = api.get(
            CITATION_SCREENINGS_API_ENDPOINT,
            **_with_ids(graph, params),
            status_counts=True,
        )
        assert response.status_code == 200
        response_data = response.json
        assert response_data and isinstance(response_data, dict)
        assert response_data == exp_data
