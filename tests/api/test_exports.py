import flask
import pytest

from colandr.lib.fileio import tabular


@pytest.mark.usefixtures("db_session")
class TestExportStudiesResource:
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
                "exports_export_studies_resource",
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
class TestExportScreeningsResource:
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
                    ["4", "citation", "included", "", "name3@example.com", "NAME3"],
                    ["4", "citation", "included", "", "name4@example.com", "NAME4"],
                ],
            ),
        ],
    )
    def test_get(self, review_id, content_type, exp_data, app, client, admin_headers):
        with app.test_request_context():
            url = flask.url_for(
                "exports_export_screenings_resource",
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
