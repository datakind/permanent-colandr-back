import flask
import pytest

from colandr.lib.fileio import tabular


# app v1
# EXPORT_STUDIES_API_ENDPOINT = "citation_imports_citations_imports_resource"
# EXPORT_SCREENINGS_API_ENDPOINT = "exports_export_screenings_resource"
# app v1.1
EXPORT_STUDIES_API_ENDPOINT = "exports.studies"
EXPORT_SCREENINGS_API_ENDPOINT = "exports.screenings"
EXPORT_PRISMA_API_ENDPOINT = "exports.prisma"


@pytest.mark.usefixtures("db_session")
class TestExportStudiesAPI:
    @pytest.mark.parametrize(
        ["review_id", "content_type", "num_rows_exp", "num_cols_exp"],
        [
            (1, "text/csv", 4, 21),
            (2, "text/csv", 2, 19),
        ],
    )
    def test_get(
        self,
        review_id,
        content_type,
        num_rows_exp,
        num_cols_exp,
        app,
        client,
        admin_headers,
    ):
        with app.test_request_context():
            url = flask.url_for(
                EXPORT_STUDIES_API_ENDPOINT,
                review_id=review_id,
                content_type=content_type,
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.text
        assert data
        if content_type == "text/csv":
            rows = list(tabular.read(data))
            assert isinstance(rows, list) and len(rows) == num_rows_exp
            assert isinstance(rows[0], list) and len(rows[0]) == num_cols_exp


@pytest.mark.usefixtures("db_session")
class TestExportScreeningsAPI:
    @pytest.mark.parametrize(
        ["review_id", "content_type", "exp_data"],
        [
            (
                1,
                "text/csv",
                [
                    [
                        "study_id",
                        "screening_stage",
                        "screening_status",
                        "screening_exclude_reasons",
                        "user_email",
                        "user_name",
                    ],
                    ["1", "citation", "included", "", "name2@example.com", "NAME2"],
                    ["2", "citation", "included", "", "name2@example.com", "NAME2"],
                    [
                        "3",
                        "citation",
                        "excluded",
                        "['REASON1', 'REASON2']",
                        "name2@example.com",
                        "NAME2",
                    ],
                    ["1", "fulltext", "included", "", "name2@example.com", "NAME2"],
                    ["1", "fulltext", "included", "", "name3@example.com", "NAME3"],
                    [
                        "2",
                        "fulltext",
                        "excluded",
                        "['REASON1', 'REASON2']",
                        "name2@example.com",
                        "NAME2",
                    ],
                ],
            ),
            (
                2,
                "text/csv",
                [
                    [
                        "study_id",
                        "screening_stage",
                        "screening_status",
                        "screening_exclude_reasons",
                        "user_email",
                        "user_name",
                    ],
                    ["4", "citation", "included", "", "name2@example.com", "NAME2"],
                    ["4", "citation", "included", "", "name3@example.com", "NAME3"],
                ],
            ),
        ],
    )
    def test_get(self, review_id, content_type, exp_data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                EXPORT_SCREENINGS_API_ENDPOINT,
                review_id=review_id,
                content_type=content_type,
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.text
        assert data
        if content_type == "text/csv":
            rows = list(tabular.read(data))
            assert rows == exp_data


@pytest.mark.usefixtures("db_session")
class TestReviewExportPrismaAPI:
    @pytest.mark.parametrize(
        ["review_id", "exp_data"],
        [
            (
                1,
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
                2,
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
    def test_get(self, review_id, exp_data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(EXPORT_PRISMA_API_ENDPOINT, review_id=review_id)
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert data == exp_data
