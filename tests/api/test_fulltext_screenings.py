"""Tests for the fulltext screenings API."""

import typing as t

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

FULLTEXT_SCREENING_API_ENDPOINT = "fulltext_screenings.fulltext_screening"
FULLTEXT_SCREENINGS_API_ENDPOINT = "fulltext_screenings.fulltext_screenings"


def _with_ids(graph: dict[str, t.Any], record: dict[str, t.Any]) -> dict[str, t.Any]:
    """Resolve expectations that name an object in ``graph`` to that object's id.

    Keys ending in ``_id`` name a graph entry -- e.g. ``{"user_id": "reviewer1"}``
    becomes ``{"user_id": <reviewer1's id>}`` -- while every other value (statuses,
    reasons, ...) is a literal and passes through untouched.
    """
    return {
        key: graph[value].id if key.endswith("_id") else value
        for key, value in record.items()
    }


@pytest.fixture
def graph(db_session, admin_user):
    """A review with two studies, each carrying a fulltext and included citation screening.

    s1 holds two fulltext screenings -- reviewer1's and reviewer2's, both included --
    and s2 holds one, reviewer1's exclusion. Citation decisions come first because
    a fulltext screening can't exist unless its citation stage is included.
    """
    reviewer1, reviewer2 = factories.create_users(
        db_session, n=2, names=["Reviewer1", "Reviewer2"]
    )
    review, studies = factories.create_screened_review(
        db_session,
        owner=admin_user,
        studies={
            "s1": {"fulltext": {"filename": "1.pdf", "text_content": "FULLTEXT1"}},
            "s2": {"fulltext": {"filename": "2.pdf", "text_content": "FULLTEXT2"}},
        },
        screening_reviewer=reviewer1,
        decisions=[
            ("s1", None, "citation", "included", None),
            ("s2", None, "citation", "included", None),
            ("s1", None, "fulltext", "included", None),
            ("s1", reviewer2, "fulltext", "included", None),
            ("s2", None, "fulltext", "excluded", ["REASON2"]),
        ],
    )
    factories.add_review_user(db_session, review, reviewer1, role="member")
    factories.add_review_user(db_session, review, reviewer2, role="member")
    return {
        "review": review,
        "reviewer1": reviewer1,
        "reviewer2": reviewer2,
        **studies,
    }


class TestFulltextScreeningAPI:
    @pytest.mark.parametrize(
        ["study_key", "fields", "status_code", "num_exp"],
        [
            ("s1", None, 200, 2),
            ("s2", None, 200, 1),
            ("s1", "id,review_id", 200, 2),
            ("s1", "fulltext_id,status", 200, 2),
            (None, None, 404, 0),
        ],
    )
    def test_get(self, study_key, fields, status_code, num_exp, graph, api):
        """Get a study's fulltext screenings."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        params = {"fields": fields} if fields is not None else {}
        response = api.get(FULLTEXT_SCREENING_API_ENDPOINT, id=study_id, **params)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            records = response.json
            exp_fields = None if fields is None else fields.split(",")
            if exp_fields is not None and "id" not in exp_fields:
                exp_fields.append("id")
            assert isinstance(records, list) and len(records) == num_exp
            for record in records:
                if "fulltext_id" in record:
                    assert record["fulltext_id"] == study_id
                if exp_fields:
                    assert "id" in record
                    assert sorted(record.keys()) == sorted(exp_fields)

    @pytest.mark.parametrize(
        ["study_key", "data", "status_code"],
        [
            # the admin modifies another reviewer's screening, naming them explicitly
            ("s2", {"user_id": "reviewer1", "status": "included"}, 200),
            (
                "s1",
                {
                    "user_id": "reviewer2",
                    "status": "excluded",
                    "exclude_reasons": ["REASON3"],
                },
                200,
            ),
            # user_id is required, so the request never reaches the missing study
            (None, {"status": "included"}, 422),
        ],
    )
    def test_put(self, study_key, data, status_code, graph, api):
        """Modify a fulltext screening."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        json_data = _with_ids(graph, data)
        response = api.put(FULLTEXT_SCREENING_API_ENDPOINT, id=study_id, json=json_data)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            obs_data = response.json
            assert {k: v for k, v in obs_data.items() if k in json_data} == json_data
            # the change is written to the screening, not merely echoed back
            fetched = api.get(FULLTEXT_SCREENING_API_ENDPOINT, id=study_id).json
            row = [item for item in fetched if item["user_id"] == json_data["user_id"]][
                0
            ]
            assert {k: v for k, v in row.items() if k in json_data} == json_data

    @pytest.mark.parametrize("study_key", ["s1", "s2"])
    def test_delete(self, study_key, graph, api):
        """Delete a fulltext screening, as an admin who hasn't screened it."""
        response = api.delete(FULLTEXT_SCREENING_API_ENDPOINT, id=graph[study_key].id)
        # NOTE: this operation is currently only allowed for the screener themself
        assert response.status_code == 403
        # get_response = client.get(url, headers=admin_headers)
        # assert get_response.status_code == 404  # not found!

    @pytest.mark.parametrize(
        ["study_key", "data", "status_code"],
        [
            # reviewer2 hasn't screened s2, whose fulltext is uploaded
            (
                "s2",
                {
                    "user_id": "reviewer2",
                    "review_id": "review",
                    "status": "included",
                },
                200,
            ),
            (None, {"status": "included"}, 404),
        ],
    )
    def test_post(self, study_key, data, status_code, graph, api):
        """Create a fulltext screening, as an admin naming the screening reviewer."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        json_data = _with_ids(graph, data)
        response = api.post(
            FULLTEXT_SCREENING_API_ENDPOINT, id=study_id, json=json_data
        )
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            obs_data = response.json
            assert {k: v for k, v in obs_data.items() if k in json_data} == json_data


class TestFulltextScreeningsAPI:
    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"fulltext_id": "s2"}, 1),
            ({"user_id": "reviewer1"}, 2),
            ({"review_id": "review"}, 3),
            ({"review_id": "review", "user_id": "reviewer2"}, 1),
        ],
    )
    def test_get(self, params, num_exp, graph, api):
        """Get fulltext screenings by fulltext, user, and/or review id."""
        response = api.get(FULLTEXT_SCREENINGS_API_ENDPOINT, **_with_ids(graph, params))
        assert response.status_code == 200
        response_data = response.json
        assert isinstance(response_data, list)
        assert len(response_data) == num_exp
