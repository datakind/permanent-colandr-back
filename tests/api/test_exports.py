"""Tests for the export API."""

import pytest

from colandr.lib.fileio import tabular

from .. import factories


pytestmark = pytest.mark.usefixtures("db_empty")

EXPORT_STUDIES_API_ENDPOINT = "exports.studies"
EXPORT_SCREENINGS_API_ENDPOINT = "exports.screenings"
EXPORT_PRISMA_API_ENDPOINT = "exports.prisma"

SCREENINGS_HEADER = [
    "study_id",
    "screening_stage",
    "screening_status",
    "screening_exclude_reasons",
    "user_email",
    "user_name",
]

# the exclusions both screening stages share; the prisma export's
# ``exclude_reason_counts`` expectation below pins these strings independently
REASONS = ["REASON1", "REASON2"]

CITATION1 = {
    "type_of_reference": "journal",
    "title": "TITLE1",
    "abstract": "ABSTRACT1",
    "pub_year": 2001,
    "pub_month": 1,
    "authors": [
        "LAST_NAME1_1, FIRST_NAME1_1",
        "LAST_NAME1_2, FIRST_NAME1_2 MIDDLE_INITIAL1_2.",
    ],
    "keywords": ["KEYWORD1_1", "KEYWORD1_2"],
    "journal_name": "JOURNAL1",
    "volume": "1",
    "issue_number": "1",
    "doi": "10.5555/111111111",
    "issn": "5555-111X",
    "publisher": "PUBLISHER1",
    "language": "English",
    "other_fields": {
        "date": "2001-01-11",
        "end_page": 11,
        "file_attachments1": "https://example.com/title1.pdf",
        "file_attachments2": "https://example.com/title1/content.html",
        "notes": ["NOTE1_1", "NOTE1_2"],
        "place_published": "PLACE1",
        "secondary_authors": ["LAST_NAME1_3, FIRST_NAME1_3"],
        "start_page": 1,
        "url": "https://example.com/title1",
    },
}
FULLTEXT1 = {
    "original_filename": "example-journal-short.pdf",
    "text_content": "This is an example text in English. Second sentence.",
}
TAGS1 = ["TAG1"]

CITATION2 = {
    "type_of_reference": "journal",
    "title": "TITLE2",
    "abstract": "ABSTRACT2",
    "pub_year": 2002,
    "pub_month": 2,
    "authors": ["LAST_NAME2_1, FIRST_NAME2_1"],
    "keywords": ["KEYWORD2"],
    "journal_name": "JOURNAL2",
    "publisher": "PUBLISHER2",
    "language": "Spanish",
    "other_fields": {"date": "2002-02-22", "url": "https://example.com/title2"},
}
FULLTEXT2 = {
    "original_filename": "example-journal.pdf",
    "text_content": "This is another example text in English.",
}
TAGS2 = ["TAG3", "TAG2", "TAG1"]

CITATION3 = {
    "type_of_reference": "book",
    "title": "TITLE3",
    "abstract": "ABSTRACT3",
    "pub_year": 2003,
    "pub_month": 3,
    "authors": ["LAST_NAME3_1, FIRST_NAME3_1"],
    "keywords": ["KEYWORD3"],
    "volume": "3",
    "publisher": "PUBLISHER3",
    "language": "English",
    "other_fields": {
        "access_date": "2013-03-03",
        "date": "2003-03-03",
        "edition": "3",
        "editors": ["LAST_NAME3_2, FIRST_NAME3_2"],
        "isbn": "555-3-33-333333-0",
        "notes": ["NOTE3"],
        "number_of_pages": 333,
        "number_of_volumes": 33,
        "place_published": "PLACE3",
        "series_title": "SERIES_TITLE3",
        "series_volume": "3",
        "short_title": "SHORT_TITLE3",
        "translators": ["LAST_NAME3_3, FIRST_NAME3_3"],
        "url": "https://example.com/title3",
    },
}

CITATION4 = {
    "type_of_reference": "newspaper",
    "title": "TITLE4",
    "abstract": "ABSTRACT4",
    "pub_year": 2004,
    "authors": ["LAST_NAME4, FIRST_NAME4"],
    "keywords": ["KEYWORD4"],
    "issue_number": "4",
    "issn": "5555-444X",
    "publisher": "PUBLISHER4",
    "language": "French",
    "other_fields": {
        "access_date": "2004-04-04",
        "column": "COLUMN4",
        "edition": "4",
        "end_page": 44,
        "frequency": "FREQUENCY4",
        "newspaper": "NEWSPAPER4",
        "notes": ["NOTE4"],
        "place_published": "PLACE4",
        "section": "SECTION4",
        "short_title": "SHORT_TITLE4",
        "start_page": 4,
        "url": "https://example.com/title4",
    },
}
TAGS4 = ["TAG4"]

# screening decisions, as ``(study, user, stage, status, reasons)`` rows
# addressed by label, in the order they're inserted
REVIEW1_DECISIONS = [
    ("s1", "uploader", "citation", "included", None),
    ("s2", "uploader", "citation", "included", None),
    ("s3", "uploader", "citation", "excluded", REASONS),
    ("s1", "uploader", "fulltext", "included", None),
    ("s1", "reviewer", "fulltext", "included", None),
    ("s2", "uploader", "fulltext", "excluded", REASONS),
]
REVIEW2_DECISIONS = [
    ("s4", "uploader", "citation", "included", None),
    ("s4", "reviewer", "citation", "included", None),
]


def _resolve_decisions(
    decisions: list[tuple], users: dict[str, object]
) -> list[tuple[str, object, str, str, list[str] | None]]:
    """Swap the user keys in a decision table for the created user objects."""
    return [
        (study_key, users[user_key], stage, status, exclude_reasons)
        for study_key, user_key, stage, status, exclude_reasons in decisions
    ]


def _exp_screening_row(graph: dict, exp_row: tuple) -> list[str]:
    """One expected screenings-CSV row, with the created study's id spliced in.

    Only the ids vary with the created objects: stages, statuses, reasons and
    reviewers' emails and names are written out literally, making this expectation
    a second, independent transcription of the seed's screenings.
    """
    study_key, stage, status, exclude_reasons, user_email, user_name = exp_row
    return [
        str(graph[study_key].id),
        stage,
        status,
        "" if exclude_reasons is None else str(exclude_reasons),
        user_email,
        user_name,
    ]


@pytest.fixture
def graph(db_session):
    """The seed's two-review dataset, rebuilt from factories.

    Review 1 holds three studies -- two with fulltexts, one excluded at citation --
    and review 2 holds one study screened twice at the citation stage. Review 1's plan
    carries two data-extraction fields whose labels the studies export adds as columns,
    and each review has imports, which the prisma export counts studies by source from.
    The acting user is the world's admin, who needs no team association.
    """
    uploader, reviewer = factories.create_users(
        db_session,
        2,
        names=["NAME2", "NAME3"],
        emails=["name2@example.com", "name3@example.com"],
    )
    users = {"uploader": uploader, "reviewer": reviewer}
    database = factories.create_data_source(
        db_session,
        source_type="database",
        source_name="SOURCE_NAME1",
        source_url="http://www.example.com/database",
    )
    gray_lit = factories.create_data_source(
        db_session, source_type="gray_literature", source_name="SOURCE_NAME2"
    )

    review1, studies1 = factories.create_screened_review(
        db_session,
        owner=uploader,
        name="NAME1",
        studies={
            "s1": {
                "citation": CITATION1,
                "fulltext": FULLTEXT1,
                "tags": TAGS1,
                "user": uploader,
                "data_source": database,
            },
            "s2": {
                "citation": CITATION2,
                "fulltext": FULLTEXT2,
                "tags": TAGS2,
                "user": uploader,
                "data_source": database,
            },
            "s3": {
                "citation": CITATION3,
                "user": uploader,
                "data_source": gray_lit,
            },
        },
        decisions=_resolve_decisions(REVIEW1_DECISIONS, users),
    )
    factories.add_review_user(db_session, review1, reviewer, role="member")
    factories.update_review_plan(
        db_session,
        review1,
        data_extraction_form=[
            {"label": "LABEL1", "field_type": "str"},
            {
                "label": "LABEL2",
                "field_type": "select_many",
                "allowed_values": ["VALUE1", "VALUE2"],
            },
        ],
    )

    review2, studies2 = factories.create_screened_review(
        db_session,
        owner=uploader,
        name="NAME2",
        studies={
            "s4": {
                "citation": CITATION4,
                "tags": TAGS4,
                "user": reviewer,
                "data_source": database,
            },
        },
        decisions=_resolve_decisions(REVIEW2_DECISIONS, users),
    )
    factories.add_review_user(db_session, review2, reviewer, role="member")

    # the seed's import history, which the prisma export counts studies by source from
    factories.create_import(
        db_session, review1, user=uploader, data_source=database, num_records=2
    )
    factories.create_import(
        db_session, review1, user=uploader, data_source=gray_lit, num_records=1
    )
    factories.create_import(
        db_session, review2, user=reviewer, data_source=database, num_records=1
    )

    return {"review1": review1, "review2": review2, **studies1, **studies2}


class TestExportStudiesAPI:
    @pytest.mark.parametrize(
        ["review_key", "num_rows_exp", "num_cols_exp"],
        [
            # three studies plus a header row; nineteen fixed columns, plus review 1's
            # two data-extraction labels
            ("review1", 4, 21),
            # one study plus a header row; no data-extraction form in review 2's plan
            ("review2", 2, 19),
        ],
    )
    def test_get(self, review_key, num_rows_exp, num_cols_exp, graph, api):
        """Export a review's studies as CSV."""
        response = api.get(
            EXPORT_STUDIES_API_ENDPOINT,
            review_id=graph[review_key].id,
            content_type="text/csv",
        )
        assert response.status_code == 200
        data = response.text
        assert data
        rows = list(tabular.read(data))
        assert isinstance(rows, list) and len(rows) == num_rows_exp
        assert isinstance(rows[0], list) and len(rows[0]) == num_cols_exp


class TestExportScreeningsAPI:
    @pytest.mark.parametrize(
        ["review_key", "exp_rows"],
        [
            (
                "review1",
                [
                    # study, stage, status, exclude reasons, user email, user name
                    ("s1", "citation", "included", None, "name2@example.com", "NAME2"),
                    ("s2", "citation", "included", None, "name2@example.com", "NAME2"),
                    (
                        "s3",
                        "citation",
                        "excluded",
                        REASONS,
                        "name2@example.com",
                        "NAME2",
                    ),
                    ("s1", "fulltext", "included", None, "name2@example.com", "NAME2"),
                    ("s1", "fulltext", "included", None, "name3@example.com", "NAME3"),
                    (
                        "s2",
                        "fulltext",
                        "excluded",
                        REASONS,
                        "name2@example.com",
                        "NAME2",
                    ),
                ],
            ),
            (
                "review2",
                [
                    ("s4", "citation", "included", None, "name2@example.com", "NAME2"),
                    ("s4", "citation", "included", None, "name3@example.com", "NAME3"),
                ],
            ),
        ],
    )
    def test_get(self, review_key, exp_rows, graph, api):
        """Export a review's screenings as CSV, in screening order."""
        response = api.get(
            EXPORT_SCREENINGS_API_ENDPOINT,
            review_id=graph[review_key].id,
            content_type="text/csv",
        )
        assert response.status_code == 200
        data = response.text
        assert data
        rows = list(tabular.read(data))
        exp_data = [SCREENINGS_HEADER]
        exp_data.extend(_exp_screening_row(graph, exp_row) for exp_row in exp_rows)
        assert rows == exp_data


class TestReviewExportPrismaAPI:
    @pytest.mark.parametrize(
        ["review_key", "exp_data"],
        [
            (
                "review1",
                {
                    "num_studies": 3,
                    "num_studies_by_source": {"database": 2, "gray_literature": 1},
                    "num_unique_studies": 3,
                    "num_screened_citations": 3,
                    "num_excluded_citations": 1,
                    "num_screened_fulltexts": 2,
                    "num_excluded_fulltexts": 1,
                    "exclude_reason_counts": {"REASON1": 2, "REASON2": 2},
                    "num_studies_data_extracted": 0,
                },
            ),
            (
                "review2",
                {
                    "num_studies": 1,
                    "num_studies_by_source": {"database": 1},
                    "num_unique_studies": 1,
                    "num_screened_citations": 1,
                    "num_excluded_citations": 0,
                    "num_screened_fulltexts": 0,
                    "num_excluded_fulltexts": 0,
                    "exclude_reason_counts": {},
                    "num_studies_data_extracted": 0,
                },
            ),
        ],
    )
    def test_get(self, review_key, exp_data, graph, api):
        """Export a review's PRISMA statistics."""
        response = api.get(EXPORT_PRISMA_API_ENDPOINT, review_id=graph[review_key].id)
        assert response.status_code == 200
        data = response.json
        assert data
        assert data == exp_data
