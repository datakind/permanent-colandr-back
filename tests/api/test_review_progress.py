"""Tests for the review progress API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

REVIEW_PROGRESS_API_ENDPOINT = "review_progress.review_progress"

REASONS = ["REASON1", "REASON2"]


@pytest.fixture
def graph(db_session):
    """Two reviews: one fully screened, one only part-way.

    Review 1's three studies have citation included/excluded then fulltext included/excluded
    and its plan has every field the planning step reports on. Review 2 has a single study
    screened once at the citation stage, so its fulltext stage still has an unscreened study
    in it, and its plan has only the objective and pico set. The acting user is the world's
    admin, who needs no team association.
    """
    owner, reviewer = factories.create_users(db_session, 2, names=["OWNER", "REVIEWER"])

    review1, _ = factories.create_screened_review(
        db_session,
        owner=owner,
        studies={
            "s1": {
                "fulltext": {
                    "text_content": "This is an example text in English. Second sentence."
                }
            },
            "s2": {
                "fulltext": {"text_content": "This is another example text in English."}
            },
            "s3": {},
        },
        screening_reviewer=reviewer,
        decisions=[
            # citation rows come first: create_screening() refuses a fulltext row on a
            # study whose citation stage isn't included yet
            ("s1", None, "citation", "included", None),
            ("s2", None, "citation", "included", None),
            # s3 is excluded at citation, and so never gets a fulltext row at all
            ("s3", None, "citation", "excluded", REASONS),
            ("s1", None, "fulltext", "included", None),
            ("s2", None, "fulltext", "excluded", REASONS),
        ],
    )
    factories.update_review_plan(
        db_session,
        review1,
        objective="OBJECTIVE",
        research_questions=["RESEARCH_QUESTION1"],
        pico={"population": "POPULATION", "intervention": "INTERVENTION"},
        keyterms=[{"term": "TERM1", "group": "GROUP1"}],
        selection_criteria=[{"label": "LABEL1", "description": "DESCRIPTION1"}],
        data_extraction_form=[{"label": "LABEL1", "field_type": "str"}],
    )

    review2, _ = factories.create_screened_review(
        db_session,
        owner=owner,
        studies={"s4": {}},
        screening_reviewer=reviewer,
        decisions=[
            ("s4", None, "citation", "included", None),
        ],
    )
    factories.update_review_plan(
        db_session,
        review2,
        objective="OBJECTIVE",
        pico={"population": "POPULATION", "intervention": "INTERVENTION"},
    )

    return {"review1": review1, "review2": review2}


class TestReviewProgressAPI:
    @pytest.mark.parametrize(
        ["review_key", "params", "status_code"],
        [
            ("review1", {}, 200),
            ("review1", {"step": "planning"}, 200),
            ("review2", {}, 200),
            ("review1", {"user_view": True}, 200),
            (None, {}, 404),
        ],
    )
    def test_get(self, review_key, params, status_code, graph, api):
        """Get progress on one or all steps of a review."""
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.get(REVIEW_PROGRESS_API_ENDPOINT, id=review_id, **params)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert data
            assert isinstance(data, dict)
            if "step" in params and params["step"] != "all":
                assert len(data) == 1
                assert params["step"] in data
            else:
                assert len(data) == 4
                assert all(
                    step in data
                    for step in [
                        "planning",
                        "citation_screening",
                        "fulltext_screening",
                        "data_extraction",
                    ]
                )

    @pytest.mark.parametrize(
        ["review_key", "exp_data"],
        [
            (
                "review1",
                {
                    "planning": {
                        "objective": True,
                        "research_questions": True,
                        "pico": True,
                        "keyterms": True,
                        "selection_criteria": True,
                        "data_extraction_form": True,
                    },
                    "citation_screening": {
                        "not_screened": 0,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 2,
                        "excluded": 1,
                    },
                    "fulltext_screening": {
                        "not_screened": 0,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 1,
                        "excluded": 1,
                    },
                    "data_extraction": {"not_started": 1, "started": 0, "finished": 0},
                },
            ),
            (
                "review2",
                {
                    "planning": {
                        "objective": True,
                        "research_questions": False,
                        "pico": True,
                        "keyterms": False,
                        "selection_criteria": False,
                        "data_extraction_form": False,
                    },
                    "citation_screening": {
                        "not_screened": 0,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 1,
                        "excluded": 0,
                    },
                    "fulltext_screening": {
                        "not_screened": 1,
                        "screened_once": 0,
                        "conflict": 0,
                        "included": 0,
                        "excluded": 0,
                    },
                    "data_extraction": {"not_started": 0, "started": 0, "finished": 0},
                },
            ),
        ],
    )
    def test_exp_result(self, review_key, exp_data, graph, api):
        """Get a review's full progress, matching the seeded world's counts."""
        response = api.get(REVIEW_PROGRESS_API_ENDPOINT, id=graph[review_key].id)
        assert response.status_code == 200
        data = response.json
        assert data == exp_data
