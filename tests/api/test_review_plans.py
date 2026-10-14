"""Tests for the review plan API."""

import pytest

from colandr import utils

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

REVIEW_PLAN_API_ENDPOINT = "review_plans.review_plan"

# seed data's review-1 plan, moved here as literals so that assertions compare
# against known values rather than against the objects they came from
PLAN_DATA = {
    "objective": "OBJECTIVE",
    "research_questions": ["Q1", "Q2", "Q3"],
    "pico": {
        "population": "POPULATION",
        "intervention": "INTERVENTION",
        "comparison": "COMPARISON",
        "outcome": "OUTCOME",
    },
    "keyterms": [
        {"term": "TERM1", "group": "GROUP1", "synonyms": ["SYNONYM1", "SYNONYM2"]},
        {"term": "TERM2", "group": "GROUP1", "synonyms": ["SYNONYM1"]},
        {"term": "TERM3", "group": "GROUP2"},
    ],
    "selection_criteria": [
        {"label": "LABEL1", "description": "DESCRIPTION1"},
        {"label": "LABEL2", "description": "DESCRIPTION2"},
    ],
    "data_extraction_form": [
        {"label": "LABEL1", "description": "DESCRIPTION1", "field_type": "str"},
        {
            "label": "LABEL2",
            "description": "DESCRIPTION2",
            "field_type": "select_many",
            "allowed_values": ["VALUE1", "VALUE2"],
        },
    ],
}
PLAN_FIELD_NAMES = [
    "objective",
    "research_questions",
    "pico",
    "keyterms",
    "selection_criteria",
    "data_extraction_form",
]


@pytest.fixture
def graph(db_session):
    """A review whose listener-created plan holds the seed's review-1 plan data."""
    review = factories.create_review(db_session, name="NAME1")
    plan = factories.update_review_plan(db_session, review, **PLAN_DATA)
    return {"review": review, "plan": plan}


class TestReviewPlanResource:
    @pytest.mark.parametrize(
        "fields",
        [None, "id,objective", "pico", "boolean_search_query"],
    )
    def test_get(self, fields, graph, api):
        """Get a review plan, whole and with field projections."""
        review = graph["review"]
        params = {"fields": fields} if fields is not None else {}
        response = api.get(REVIEW_PLAN_API_ENDPOINT, id=review.id, **params)
        assert response.status_code == 200
        data = response.json
        exp_fields = None if fields is None else fields.split(",")
        if exp_fields is not None and "id" not in exp_fields:
            exp_fields.append("id")
        assert "id" in data
        assert data["id"] == review.id
        for field in ["objective", "pico"]:
            if exp_fields is None or field in exp_fields:
                assert data[field] == PLAN_DATA[field]
        if exp_fields is None or "boolean_search_query" in exp_fields:
            assert data["boolean_search_query"] == utils.get_boolean_search_query(
                PLAN_DATA["keyterms"]
            )
        if exp_fields:
            assert sorted(data.keys()) == sorted(exp_fields)

    @pytest.mark.parametrize(
        ["review_key", "data", "status_code"],
        [
            ("review", {"objective": "NEW_OBJECTIVE1"}, 200),
            ("review", {"research_questions": ["NEW_Q1", "NEW_Q2"]}, 200),
            (
                "review",
                {
                    "keyterms": [
                        {"group": "GROUP1", "term": "TERM1", "synonyms": ["SYN1"]},
                        {"group": "GROUP1", "term": "TERM2"},
                    ]
                },
                200,
            ),
            (
                "review",
                {
                    "keyterms": [
                        {
                            "group": "GROUP1",
                            "term": "TERM1",
                            "synonyms": "SYN1, SYN2, SYN3",
                        },
                    ]
                },
                200,
            ),
            (None, {"objective": "NEW_OBJECTIVE999"}, 404),
        ],
    )
    def test_put(self, review_key, data, status_code, graph, api):
        """Modify a review plan, as an owner of the review."""
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.put(REVIEW_PLAN_API_ENDPOINT, id=review_id, json=data)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            obs_data = response.json
            # the response isn't a verbatim echo of the payload -- the input schema
            # coerces some fields, e.g. comma-delimited keyterm synonyms become a list --
            # so check the response against a follow-up read instead
            fetched = api.get(REVIEW_PLAN_API_ENDPOINT, id=review_id).json
            for key in data:
                assert key in obs_data
                assert obs_data[key]  # set to something, not dropped or nulled out
                assert fetched[key] == obs_data[key]  # and persisted as returned

    def test_delete(self, graph, api):
        """Delete a review plan, which merely empties out its fields."""
        review = graph["review"]
        # the plan starts out populated, so the assertions below mean something
        before = api.get(REVIEW_PLAN_API_ENDPOINT, id=review.id).json
        for key in PLAN_FIELD_NAMES:
            assert before[key]
        response = api.delete(REVIEW_PLAN_API_ENDPOINT, id=review.id)
        assert response.status_code == 204
        get_response = api.get(REVIEW_PLAN_API_ENDPOINT, id=review.id)
        get_data = get_response.json
        for key in PLAN_FIELD_NAMES:
            assert not get_data[key]
