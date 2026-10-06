"""Tests for the citations API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

CITATION_API_ENDPOINT = "citations.citation"
CITATIONS_API_ENDPOINT = "citations.citations"

CITATION1 = {
    "type_of_reference": "journal",
    "title": "TITLE1",
    "abstract": "ABSTRACT1",
    "pub_year": 2020,
    "authors": ["LASTNAME1, FIRSTNAME1"],
    "keywords": ["KW1"],
}
CITATION2 = {
    "type_of_reference": "journal",
    "title": "TITLE2",
    "abstract": "ABSTRACT2",
    "journal_name": "JOURNAL2",
    "doi": "10.1234/DOI2",
    "keywords": ["KW2"],
}


@pytest.fixture
def graph(db_session):
    """A review with two studies, each carrying an explicit citation dict.

    The acting user is the world's admin, who needs no team association.
    ``citations`` holds snapshots of the dicts, not the studies' own attributes:
    ``create_study()`` keeps the object it's handed, so a study's ``citation``
    *is* the test's dict, shared with the endpoint under test.
    """
    review = factories.create_review(db_session)
    s1, s2 = factories.create_studies(
        db_session, 2, review=review, citations=[CITATION1, CITATION2]
    )
    return {
        "s1": s1,
        "s2": s2,
        "citations": {"s1": dict(CITATION1), "s2": dict(CITATION2)},
    }


class TestCitationAPI:
    @pytest.mark.parametrize(
        ["study_key", "fields", "status_code"],
        [
            ("s1", None, 200),
            ("s2", None, 200),
            ("s1", "id,title", 200),
            ("s1", "abstract", 200),
            (None, None, 404),
        ],
    )
    def test_get(self, study_key, fields, status_code, graph, api):
        """Get a study's citation, as the world's admin."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        params = {"fields": fields} if fields is not None else {}
        response = api.get(CITATION_API_ENDPOINT, id=study_id, **params)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            exp_citation = graph["citations"][study_key]
            # the requested fields, plus "id", which is always included
            exp_fields = None if fields is None else sorted({*fields.split(","), "id"})
            assert data["id"] == study_id
            exp_data = {
                key: val
                for key, val in exp_citation.items()
                if exp_fields is None or key in exp_fields
            }
            # every wanted citation field comes back with the value we created, and no
            # unwanted ones come with it
            assert {k: v for k, v in data.items() if k in exp_data} == exp_data
            if exp_fields is not None:
                assert sorted(data.keys()) == exp_fields

    @pytest.mark.parametrize(
        ["study_key", "data", "status_code"],
        [
            ("s1", {"title": "NEW_TITLE1"}, 200),
            ("s1", {"abstract": "NEW_ABSTRACT1"}, 200),
            ("s2", {"title": "NEW_TITLE2", "abstract": "NEW_ABSTRACT2"}, 200),
            (None, {"title": "NEW_TITLE999"}, 404),
        ],
    )
    def test_put(self, study_key, data, status_code, graph, api):
        """Modify a study's citation, merging the given fields into it."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.put(CITATION_API_ENDPOINT, id=study_id, json=data)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            obs_data = response.json
            assert {k: v for k, v in obs_data.items() if k in data} == data
            # the merge is written to the study, not merely echoed back
            fetched = api.get(CITATION_API_ENDPOINT, id=study_id).json
            assert {k: v for k, v in fetched.items() if k in data} == data

    @pytest.mark.parametrize("study_key", ["s1", "s2"])
    def test_delete(self, study_key, graph, api):
        """Delete a study's citation, emptying it out."""
        study = graph[study_key]
        response = api.delete(CITATION_API_ENDPOINT, id=study.id)
        assert response.status_code == 204
        # TODO: decide on delete behavior for study.citation
        # get_response = client.get(url, headers=admin_headers)
        # assert get_response.status_code == 404  # not found!
        get_response = api.get(CITATION_API_ENDPOINT, id=study.id)
        assert get_response.json == {}  # empty!


class TestCitationsAPI:
    @pytest.fixture
    def review(self, db_session):
        """A review to add citations to; the world's admin needs no team association."""
        return factories.create_review(db_session)

    @pytest.mark.parametrize(
        ["params", "data"],
        [
            (
                {
                    "source_type": "database",
                    "source_name": "SOURCE_NAMEX",
                    "source_url": "http://www.example.com/SOURCEX",
                },
                {"title": "TITLEX", "abstract": "ABSTRACTX"},
            ),
            (
                {
                    "source_type": "database",
                    "source_name": "SOURCE_NAMEY",
                    "status": "included",
                },
                {"title": "TITLEY", "abstract": "ABSTRACTY"},
            ),
        ],
    )
    def test_post(self, params, data, review, api):
        """Create a citation in a review, naming the data source it came from."""
        response = api.post(
            CITATIONS_API_ENDPOINT, json=data, review_id=review.id, **params
        )
        assert response.status_code == 200
        response_data = response.json
        assert {k: response_data[k] for k in data.keys()} == data
        assert response_data["review_id"] == review.id

        # citation is stored on a new study, which the read endpoints can see
        study = api.get("studies.study", id=response_data["id"]).json
        assert {k: study["citation"][k] for k in data} == data
        assert study["citation_status"] == params.get("status", "not_screened")
