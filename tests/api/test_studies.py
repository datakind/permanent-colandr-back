"""Tests for the studies API."""

import typing as t

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

STUDY_API_ENDPOINT = "studies.study"
STUDIES_API_ENDPOINT = "studies.studies"


def _with_ids(graph: dict[str, t.Any], exp_data: dict[str, t.Any]) -> dict[str, t.Any]:
    """Resolve expectations that name an object in ``graph`` to that object's id.

    Keys ending in ``_id`` name a graph entry -- e.g. ``{"user_id": "member"}`` becomes
    ``{"user_id": <member's id>}`` -- while every other value (tags, names, ...) is a
    literal and passes through untouched.
    """
    return {
        key: graph[value].id if key.endswith("_id") else value
        for key, value in exp_data.items()
    }


@pytest.fixture
def graph(db_session, admin_user):
    """An admin, a member, an outsider, one data source, and two reviews.

    Admin owns both reviews; member belongs to review 1 only, outsider belongs to neither.
    Review 1 has three studies: s1 screened through fulltext stage, s2 accepted at citation,
    s3 excluded at citation. Review 2 holds s4, which requires two fulltext reviewers.
    """
    member, outsider = factories.create_users(
        db_session, n=2, names=["Member", "Outwider"]
    )
    data_source = factories.create_data_source(db_session, source_name="SOURCE1")
    review1 = factories.create_review_with_team(
        db_session, owner=admin_user, members=[member], name="NAME1"
    )
    review2 = factories.create_review_with_team(
        db_session, owner=admin_user, name="NAME2"
    )
    s1, s2, s3 = factories.create_studies(
        db_session,
        3,
        review=review1,
        users=member,
        data_sources=data_source,
        tagss=[["TAG1"], ["TAG2"], ["TAG3"]],
        citations=[
            {
                "type_of_reference": "journal",
                "title": "TITLE1 study one",
                "abstract": "ABSTRACT1",
                "keywords": ["KW1"],
            },
            {
                "type_of_reference": "journal",
                "title": "TITLE2 study two",
                "abstract": "ABSTRACT2",
                "keywords": ["KW2"],
            },
            {
                "type_of_reference": "journal",
                "title": "TITLE3 study three",
                "abstract": "ABSTRACT3",
                "keywords": ["KW3"],
            },
        ],
    )
    s4 = factories.create_study(
        db_session,
        review=review2,
        user=admin_user,
        data_source=data_source,
        tags=["TAG4"],
        num_fulltext_reviewers=2,
        citation={
            "type_of_reference": "journal",
            "title": "TITLE4 study four",
            "abstract": "ABSTRACT4",
            "keywords": ["KW4"],
        },
    )
    # screen citation stages before fulltext ones: a citation decision other than
    # "included" forbids a fulltext screening from existing at all
    factories.create_screenings(
        db_session,
        4,
        studies=[s1, s1, s2, s3],
        users=member,
        stages=["citation", "fulltext", "citation", "citation"],
        statuses=["included", "included", "included", "excluded"],
    )
    factories.create_screening(db_session, study=s4, user=admin_user, status="included")
    return {
        "admin": admin_user,
        "member": member,
        "outsider": outsider,
        "data_source": data_source,
        "review1": review1,
        "review2": review2,
        "s1": s1,
        "s2": s2,
        "s3": s3,
        "s4": s4,
    }


class TestStudyAPI:
    ## GET ##

    @pytest.mark.parametrize(
        ["actor", "study_key", "fields", "exp_data"],
        [
            (
                "admin",
                "s1",
                None,
                {
                    "user_id": "member",
                    "review_id": "review1",
                    "data_source_id": "data_source",
                    "tags": ["TAG1"],
                },
            ),
            (
                "member",
                "s2",
                None,
                {
                    "user_id": "member",
                    "review_id": "review1",
                    "data_source_id": "data_source",
                    "tags": ["TAG2"],
                },
            ),
            (
                "admin",
                "s1",
                "id,user_id,review_id",
                {"user_id": "member", "review_id": "review1"},
            ),
            ("member", "s1", "data_source_id", {"data_source_id": "data_source"}),
        ],
    )
    def test_get(self, actor, study_key, fields, exp_data, graph, api):
        """Get a study, as an admin or as a member of its review."""
        study = graph[study_key]
        params = {"fields": fields} if fields is not None else {}
        response = api.as_user(graph[actor]).get(
            STUDY_API_ENDPOINT, id=study.id, **params
        )
        assert response.status_code == 200
        data = response.json
        assert "id" in data and data["id"] == study.id
        exp = _with_ids(graph, exp_data)
        assert {k: v for k, v in data.items() if k in exp} == exp

    @pytest.mark.parametrize(
        ["actor", "study_key", "status_code"],
        [
            ("admin", None, 404),
            ("outsider", "s1", 403),
        ],
    )
    def test_get_errors(self, actor, study_key, status_code, graph, api):
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.as_user(graph[actor]).get(STUDY_API_ENDPOINT, id=study_id)
        assert response.status_code == status_code

    ## PUT ##

    @pytest.mark.parametrize(
        ["actor", "study_key", "data"],
        [
            ("admin", "s1", {"tags": ["TAG1", "TAG2"]}),
            (
                "member",
                "s1",
                {"tags": ["THIS-IS-A-REALLLLLLLLLLLLLLLLLLLLLLLLLLY-LONG-TAG1"]},
            ),
        ],
    )
    def test_put(self, actor, study_key, data, graph, api):
        """Modify a study, as an admin or as a member of its review."""
        study = graph[study_key]
        response = api.as_user(graph[actor]).put(
            STUDY_API_ENDPOINT, id=study.id, json=data
        )
        assert response.status_code == 200
        obs_data = response.json
        assert "id" in obs_data and obs_data["id"] == study.id
        assert {k: v for k, v in obs_data.items() if k in data} == data

    @pytest.mark.parametrize(
        ["actor", "study_key", "data", "status_code"],
        [
            # only admins and review members can modify studies
            ("outsider", "s1", {"tags": ["NEW_TAG1"]}, 403),
            # tags are capped at 64 characters
            ("member", "s1", {"tags": ["X" * 65]}, 422),
            # data extraction can't begin before a study passes fulltext screening
            ("member", "s2", {"data_extraction_status": "finished"}, 403),
            # only existing studies can be modified
            ("admin", None, {"tags": ["NEW_TAG1"]}, 404),
        ],
    )
    def test_put_errors(self, actor, study_key, data, status_code, graph, api):
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.as_user(graph[actor]).put(
            STUDY_API_ENDPOINT, id=study_id, json=data
        )
        assert response.status_code == status_code

    ## DELETE ##

    @pytest.mark.parametrize(
        ["actor", "study_key"],
        [
            ("admin", "s1"),
            ("member", "s2"),
        ],
    )
    def test_delete(self, actor, study_key, graph, api):
        """Delete a study, as an admin or as a member of its review."""
        study = graph[study_key]
        del_response = api.as_user(graph[actor]).delete(STUDY_API_ENDPOINT, id=study.id)
        assert del_response.status_code == 204
        get_response = api.get(STUDY_API_ENDPOINT, id=study.id)
        assert get_response.status_code == 404

    @pytest.mark.parametrize(
        ["actor", "study_key", "status_code"],
        [
            ("admin", None, 404),  # only existing studies can be deleted
            # only admins and review members can delete studies
            ("outsider", "s1", 403),
        ],
    )
    def test_delete_errors(self, actor, study_key, status_code, graph, api):
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        response = api.as_user(graph[actor]).delete(STUDY_API_ENDPOINT, id=study_id)
        assert response.status_code == status_code


class TestStudiesResource:
    ## GET ##

    @pytest.mark.parametrize(
        ["review_key", "params", "exp_labels"],
        [
            ("review1", {}, ["s1", "s2", "s3"]),
            ("review2", {}, ["s4"]),
            ("review1", {"dedupe_status": "not_duplicate"}, ["s1", "s2", "s3"]),
            ("review1", {"citation_status": "included"}, ["s1", "s2"]),
            ("review1", {"citation_status": "excluded"}, ["s3"]),
            ("review1", {"fulltext_status": "included"}, ["s1"]),
            # the admin screens nothing, so no study is waiting on them to co-screen
            ("review1", {"citation_status": "awaiting_coscreener"}, []),
            ("review2", {"fulltext_status": "pending"}, ["s4"]),
            ("review1", {"num_citation_reviewers": 1}, ["s1", "s2", "s3"]),
            ("review1", {"num_citation_reviewers": 2}, []),
            ("review2", {"num_fulltext_reviewers": 1}, []),
            ("review2", {"num_fulltext_reviewers": 2}, ["s4"]),
            ("review1", {"tag": "TAG1"}, ["s1"]),
            ("review1", {"tag": "TAG2"}, ["s2"]),
            # extraction status is only reported for studies included at fulltext
            ("review1", {"data_extraction_status": "not_started"}, ["s1"]),
            ("review1", {"tsquery": "TITLE1"}, ["s1"]),
            ("review1", {"order_by": "relevance"}, ["s1", "s2", "s3"]),
            ("review1", {"tsquery": "TITLE1", "order_by": "relevance"}, ["s1"]),
            ("review1", {"order_by": "recency"}, ["s1", "s2", "s3"]),
            ("review1", {"order_by": "recency", "page": 0, "per_page": 1}, ["s3"]),
            ("review1", {"order_by": "recency", "page": 1, "per_page": 1}, ["s2"]),
        ],
    )
    def test_get(self, review_key, params, exp_labels, graph, api):
        """Get studies in a review, filtered and ordered by the request's params.

        Recency orders by id descending, so the paginated rows keep their semantics;
        relevance ordering is randomized without a trained ranker model, so ids are
        compared as an unordered set.
        """
        review = graph[review_key]
        response = api.as_user(graph["admin"]).get(
            STUDIES_API_ENDPOINT, review_id=review.id, **params
        )
        assert response.status_code == 200
        obs_data = response.json
        assert isinstance(obs_data, list)
        assert sorted(study["id"] for study in obs_data) == sorted(
            graph[label].id for label in exp_labels
        )

    @pytest.mark.parametrize(
        ["actor", "review_key", "status_code"],
        [
            ("admin", None, 404),
            ("outsider", "review1", 403),
        ],
    )
    def test_get_errors(self, actor, review_key, status_code, graph, api):
        review_id = (
            factories.NOT_FOUND_ID if review_key is None else graph[review_key].id
        )
        response = api.as_user(graph[actor]).get(
            STUDIES_API_ENDPOINT, review_id=review_id
        )
        assert response.status_code == status_code
