import flask
import pytest
from colandr.lib.fileio import tabular


class TestReviewExportPrismaResource:
    @pytest.mark.parametrize(
        ["review_id", "exp_data"],
        [
            (
                1,
                {
                    "num_studies_by_source": {"database": 2, "gray_literature": 1},
                    "num_unique_studies": 3,
                    "num_screened_citations": 3,
                    "num_excluded_citations": 1,
                    "num_screened_fulltexts": 2,
                    "num_excluded_fulltexts": 1,
                    "exclude_reason_counts": {"REASON1": 1, "REASON2": 1},
                    "num_studies_data_extracted": 0,
                },
            ),
            (
                2,
                {
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
            url = flask.url_for(
                "review_exports_review_export_prisma_resource", id=review_id
            )
        response = client.get(url, headers=admin_headers)
        assert response.status_code == 200
        data = response.json
        assert data
        assert data == exp_data


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
