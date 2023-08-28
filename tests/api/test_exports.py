import flask
import pytest

from colandr.lib.fileio import tabular


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


class TestExportScreeningsResource:
    @pytest.mark.parametrize(
        ["review_id", "content_type", "exp_data"],
        [
            (
                1,
                "text/csv",
                [
                    [
                        "screening_id",
                        "screening_status",
                        "screening_exclude_reasons",
                        "screening_stage",
                        "study_id",
                        "user_email",
                        "user_name",
                    ],
                    [
                        "1",
                        "included",
                        "",
                        "citation",
                        "1",
                        "name2@example.com",
                        "NAME2",
                    ],
                    [
                        "2",
                        "included",
                        "",
                        "citation",
                        "2",
                        "name2@example.com",
                        "NAME2",
                    ],
                    [
                        "3",
                        "excluded",
                        "['REASON1', 'REASON2']",
                        "citation",
                        "3",
                        "name2@example.com",
                        "NAME2",
                    ],
                    [
                        "1",
                        "included",
                        "",
                        "fulltext",
                        "1",
                        "name2@example.com",
                        "NAME2",
                    ],
                    [
                        "2",
                        "included",
                        "",
                        "fulltext",
                        "1",
                        "name3@example.com",
                        "NAME3",
                    ],
                    [
                        "3",
                        "excluded",
                        "['REASON1', 'REASON2']",
                        "fulltext",
                        "2",
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
                        "screening_id",
                        "screening_status",
                        "screening_exclude_reasons",
                        "screening_stage",
                        "study_id",
                        "user_email",
                        "user_name",
                    ],
                    [
                        "4",
                        "included",
                        "",
                        "citation",
                        "4",
                        "name3@example.com",
                        "NAME3",
                    ],
                    [
                        "5",
                        "included",
                        "",
                        "citation",
                        "4",
                        "name4@example.com",
                        "NAME4",
                    ],
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
            breakpoint()
            assert rows == exp_data
