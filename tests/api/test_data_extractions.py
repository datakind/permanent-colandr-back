"""Tests for the data extractions API."""

import pytest

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

# NOTE: the blueprint is "data extractions" (with a space), so that's the endpoint prefix
EXTRACTION_API_ENDPOINT = "data extractions.data_extraction"

EXTRACTION_FORM = [
    {"label": "LABEL_STR", "field_type": "str"},
    {"label": "LABEL_INT", "field_type": "int"},
    {"label": "LABEL_FLOAT", "field_type": "float"},
    {"label": "LABEL_BOOL", "field_type": "bool"},
    {"label": "LABEL_DATE", "field_type": "date"},
    {
        "label": "LABEL_SELECT_ONE",
        "field_type": "select_one",
        "allowed_values": ["VALUE1", "VALUE2"],
    },
    {
        "label": "LABEL_SELECT_MANY",
        "field_type": "select_many",
        "allowed_values": ["VALUE1", "VALUE2"],
    },
    {"label": "LABEL_COUNTRY", "field_type": "country"},
]


@pytest.fixture
def graph(db_session, admin_user):
    """Three reviews and four studies, one extraction per included study.

    The acting user is the world's admin; ``outsider`` is on no team.

    - review1 (active, full extraction form): s1 was included at citation *and* fulltext,
      so the screening listener created its DataExtraction; s2 was included at citation
      only, so it has none
    - review2 (frozen): s3 has an extraction to check read/write asymmetry
    - review3 (active, default empty form): s4 has an extraction but no form to validate
    """
    outsider = factories.create_user(db_session)
    review1, studies1 = factories.create_screened_review(
        db_session,
        owner=admin_user,
        studies={"s1": {}, "s2": {}},
        screening_reviewer=admin_user,
        decisions=[
            ("s1", None, "citation", "included", None),
            ("s1", None, "fulltext", "included", None),
            ("s2", None, "citation", "included", None),
        ],
    )
    factories.update_review_plan(
        db_session, review1, data_extraction_form=EXTRACTION_FORM
    )
    review2, studies2 = factories.create_screened_review(
        db_session,
        owner=admin_user,
        status="frozen",
        studies={"s3": {}},
        screening_reviewer=admin_user,
        decisions=[
            ("s3", None, "citation", "included", None),
            ("s3", None, "fulltext", "included", None),
        ],
    )
    review3, studies3 = factories.create_screened_review(
        db_session,
        owner=admin_user,
        studies={"s4": {}},
        screening_reviewer=admin_user,
        decisions=[
            ("s4", None, "citation", "included", None),
            ("s4", None, "fulltext", "included", None),
        ],
    )
    return {
        "review1": review1,
        "review2": review2,
        "review3": review3,
        "s1": studies1["s1"],
        "s2": studies1["s2"],
        "s3": studies2["s3"],
        "s4": studies3["s4"],
        "outsider": outsider,
    }


class TestDataExtractionAPI:
    @pytest.mark.parametrize(
        ["study_key", "actor", "status_code"],
        [
            ("s1", "admin", 200),
            ("s2", "admin", 404),  # never included at fulltext, so no extraction row
            (None, "admin", 404),
            ("s1", "outsider", 403),
            # FIXME: reads ignore if_frozen, so a frozen review's extractions stay readable
            # writes (below) are correctly refused
            ("s3", "admin", 200),
        ],
    )
    def test_get(self, study_key, actor, status_code, graph, api):
        """Get the data extraction for a single study."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        client = api if actor == "admin" else api.as_user(graph[actor])
        response = client.get(EXTRACTION_API_ENDPOINT, id=study_id)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert data["study_id"] == study_id
            assert data["review_id"] == graph[study_key].review_id
            # FIXME: extracted_items is created with a '{}' server default, not '[]'
            # see corresponding comment in colandr/models.py for more details
            assert data["extracted_items"] == []

    @pytest.mark.parametrize(
        ["data", "exp_items", "status_code"],
        [
            # happy paths, one row per field_type, with the value the route stores
            (
                [{"label": "LABEL_STR", "value": "TEXT"}],
                [{"label": "LABEL_STR", "value": "TEXT"}],
                200,
            ),
            (
                [{"label": "LABEL_INT", "value": "42"}],
                [{"label": "LABEL_INT", "value": 42}],
                200,
            ),
            (
                [{"label": "LABEL_FLOAT", "value": "4.5"}],
                [{"label": "LABEL_FLOAT", "value": 4.5}],
                200,
            ),
            (
                [{"label": "LABEL_BOOL", "value": "true"}],
                [{"label": "LABEL_BOOL", "value": True}],
                200,
            ),
            (
                [{"label": "LABEL_BOOL", "value": "f"}],
                [{"label": "LABEL_BOOL", "value": False}],
                200,
            ),
            (
                [{"label": "LABEL_DATE", "value": "2020-01-02"}],
                [{"label": "LABEL_DATE", "value": "2020-01-02 00:00:00"}],
                200,
            ),
            (
                [{"label": "LABEL_SELECT_ONE", "value": "VALUE2"}],
                [{"label": "LABEL_SELECT_ONE", "value": "VALUE2"}],
                200,
            ),
            (
                [{"label": "LABEL_SELECT_MANY", "value": ["VALUE1", "VALUE2"]}],
                [{"label": "LABEL_SELECT_MANY", "value": ["VALUE1", "VALUE2"]}],
                200,
            ),
            # errors, all 400 with the offending label named in the message
            ([{"label": "LABEL_COUNTRY", "value": "US"}], None, 400),
            ([{"label": "NO_SUCH_LABEL", "value": "X"}], None, 400),
            ([{"label": "LABEL_SELECT_ONE", "value": "VALUE9"}], None, 400),
            ([{"label": "LABEL_INT", "value": "not-an-int"}], None, 400),
            ([{"label": "LABEL_FLOAT", "value": "not-a-float"}], None, 400),
            ([{"label": "LABEL_DATE", "value": "not-a-date"}], None, 400),
            ([{"label": "LABEL_BOOL", "value": "maybe"}], None, 400),
            ([{"label": "LABEL_STR", "value": None}], None, 422),
            # a bare string for select_many validates character by character
            ([{"label": "LABEL_SELECT_MANY", "value": "VALUE1"}], None, 400),
        ],
    )
    def test_put(self, data, exp_items, status_code, graph, api):
        """Validate and store extracted items against the review's extraction form."""
        study = graph["s1"]
        response = api.put(EXTRACTION_API_ENDPOINT, id=study.id, json=data)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            assert response.json["extracted_items"] == exp_items
            assert (
                api.get(EXTRACTION_API_ENDPOINT, id=study.id).json["extracted_items"]
                == exp_items
            )
            assert study.data_extraction_status == "started"
        else:
            assert response.json["message"]

    def test_put_country_not_implemented(self, graph, api):
        """A 'country' field is refused with a fixed message.

        FIXME: branch is a placeholder, so a review whose extraction form contains
        a country field can't complete extraction. Implement the validation!
        """
        response = api.put(
            EXTRACTION_API_ENDPOINT,
            id=graph["s1"].id,
            json=[{"label": "LABEL_COUNTRY", "value": "US"}],
        )
        assert response.status_code == 400
        assert "has not yet been implemented" in response.json["message"]

    def test_put_merges_with_existing_items(self, graph, api):
        """A second PUT keeps labels it doesn't mention."""
        study = graph["s1"]
        first = [{"label": "LABEL_STR", "value": "TEXT"}]
        second = [{"label": "LABEL_INT", "value": 7}]
        assert (
            api.put(EXTRACTION_API_ENDPOINT, id=study.id, json=first).status_code == 200
        )
        response = api.put(EXTRACTION_API_ENDPOINT, id=study.id, json=second)
        assert response.status_code == 200
        assert response.json["extracted_items"] == [
            {"label": "LABEL_STR", "value": "TEXT"},
            {"label": "LABEL_INT", "value": 7},
        ]

    @pytest.mark.parametrize(
        ["study_key", "actor", "status_code"],
        [
            ("s2", "admin", 404),  # no extraction to modify
            (None, "admin", 404),
            ("s1", "outsider", 403),
            ("s3", "admin", 403),  # frozen reviews are read-only
            ("s4", "admin", 400),  # no form; see test_put_without_a_form
        ],
    )
    def test_put_errors(self, study_key, actor, status_code, graph, api):
        """Refuse writes the caller isn't allowed, or isn't able, to make."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        client = api if actor == "admin" else api.as_user(graph[actor])
        response = client.put(
            EXTRACTION_API_ENDPOINT,
            id=study_id,
            json=[{"label": "LABEL_STR", "value": "TEXT"}],
        )
        assert response.status_code == status_code

    def test_put_without_a_form(self, graph, api):
        """A review with no extraction form rejects every label.

        FIXME: DataExtractionAPI.put() intends to answer 403 here, but its guard is
        `if not data_extraction_form`, which tests a one-column Row (always truthy),
        so the branch is effectively dead, and the result is a 400 from label validation.
        Should be 403, naming the missing form.
        """
        response = api.put(
            EXTRACTION_API_ENDPOINT,
            id=graph["s4"].id,
            json=[{"label": "LABEL_STR", "value": "TEXT"}],
        )
        assert response.status_code == 400
        assert "LABEL_STR" in response.json["message"]

    def test_put_finished_extraction(self, graph, api):
        """A finished extraction is locked against further modification."""
        # no data-extraction endpoint sets "finished"; the studies endpoint does
        assert (
            api.put(
                "studies.study",
                id=graph["s1"].id,
                json={"data_extraction_status": "finished"},
            ).status_code
            == 200
        )
        response = api.put(
            EXTRACTION_API_ENDPOINT,
            id=graph["s1"].id,
            json=[{"label": "LABEL_STR", "value": "TEXT"}],
        )
        assert response.status_code == 403

    def test_delete_labels(self, graph, api):
        """Deleting some labels keeps the rest, and the study stays 'started'."""
        study = graph["s1"]
        api.put(
            EXTRACTION_API_ENDPOINT,
            id=study.id,
            json=[
                {"label": "LABEL_STR", "value": "TEXT"},
                {"label": "LABEL_INT", "value": 7},
            ],
        )
        response = api.delete(EXTRACTION_API_ENDPOINT, id=study.id, labels="LABEL_STR")
        assert response.status_code == 204
        assert api.get(EXTRACTION_API_ENDPOINT, id=study.id).json[
            "extracted_items"
        ] == [{"label": "LABEL_INT", "value": 7}]
        assert study.data_extraction_status == "started"

    def test_delete_all_labels(self, graph, api):
        """Deleting every label empties the record and resets the study status."""
        study = graph["s1"]
        api.put(
            EXTRACTION_API_ENDPOINT,
            id=study.id,
            json=[{"label": "LABEL_STR", "value": "TEXT"}],
        )
        response = api.delete(EXTRACTION_API_ENDPOINT, id=study.id, labels="LABEL_STR")
        assert response.status_code == 204
        assert (
            api.get(EXTRACTION_API_ENDPOINT, id=study.id).json["extracted_items"] == []
        )
        assert study.data_extraction_status == "not_started"

    def test_delete_without_labels(self, graph, api):
        """Omitting labels clears everything, regardless of what was stored."""
        study = graph["s1"]
        api.put(
            EXTRACTION_API_ENDPOINT,
            id=study.id,
            json=[{"label": "LABEL_STR", "value": "TEXT"}],
        )
        response = api.delete(EXTRACTION_API_ENDPOINT, id=study.id)
        assert response.status_code == 204
        assert (
            api.get(EXTRACTION_API_ENDPOINT, id=study.id).json["extracted_items"] == []
        )
        assert study.data_extraction_status == "not_started"

    def test_delete_unknown_label(self, graph, api):
        """Naming a label that isn't stored is a no-op, not an error."""
        study = graph["s1"]
        api.put(
            EXTRACTION_API_ENDPOINT,
            id=study.id,
            json=[{"label": "LABEL_STR", "value": "TEXT"}],
        )
        response = api.delete(
            EXTRACTION_API_ENDPOINT, id=study.id, labels="NO_SUCH_LABEL"
        )
        assert response.status_code == 204
        assert api.get(EXTRACTION_API_ENDPOINT, id=study.id).json[
            "extracted_items"
        ] == [{"label": "LABEL_STR", "value": "TEXT"}]

    def test_delete_before_any_put(self, graph, api):
        """Deleting labels from an untouched extraction clears it and its status.

        FIXME: the row's extracted_items is the '{}' server default, not '[]'. It's empty,
        so filtering it is a silent no-op and the status still resets; a non-empty object
        would in fact raise. See corresponding comment in colandr/models.py.
        """
        study = graph["s1"]
        response = api.delete(EXTRACTION_API_ENDPOINT, id=study.id, labels="LABEL_STR")
        assert response.status_code == 204
        assert study.data_extraction_status == "not_started"

    @pytest.mark.parametrize(
        ["study_key", "actor", "status_code"],
        [
            ("s2", "admin", 404),
            (None, "admin", 404),
            ("s1", "outsider", 403),
            ("s3", "admin", 403),  # frozen reviews are read-only
        ],
    )
    def test_delete_errors(self, study_key, actor, status_code, graph, api):
        """Refuse deletions the caller isn't allowed to make."""
        study_id = factories.NOT_FOUND_ID if study_key is None else graph[study_key].id
        client = api if actor == "admin" else api.as_user(graph[actor])
        assert (
            client.delete(EXTRACTION_API_ENDPOINT, id=study_id).status_code
            == status_code
        )
