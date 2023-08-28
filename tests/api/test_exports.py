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
