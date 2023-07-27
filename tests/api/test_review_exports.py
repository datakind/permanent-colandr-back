import flask
import pytest
from colandr.lib.fileio import tabular


class TestReviewExportStudiesResource:
    @pytest.mark.parametrize(
        ["review_id", "num_rows_exp", "num_cols_exp"],
        [
            (1, 4, 19),
            (2, 2, 17),
        ],
    )
    def test_get(
        self, review_id, num_rows_exp, num_cols_exp, app, client, admin_headers
    ):
        with app.test_request_context():
            url = flask.url_for(
                "review_exports_review_export_studies_resource", id=review_id
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.text
        assert data
        rows = list(tabular.read(data))
        assert isinstance(rows, list) and len(rows) == num_rows_exp
        assert isinstance(rows[0], list) and len(rows[0]) == num_cols_exp
