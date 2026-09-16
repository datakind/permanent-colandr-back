import pytest


CITATION_IMPORTS_API_ENDPOINT = "citation_imports.citation_imports"


@pytest.mark.usefixtures("db_session")
class TestCitationsImportsResource:
    @pytest.mark.parametrize(
        ["params", "file_name"],
        [
            (
                {
                    "review_id": 1,
                    "status": "included",
                    "source_type": "database",
                },
                "example.ris",
            ),
            (
                {
                    "review_id": 1,
                    "status": "included",
                    "source_type": "database",
                },
                "example.bib",
            ),
        ],
    )
    def test_post(self, params, file_name, db_session, api, request):
        dir_path = request.config.rootpath
        file_path = dir_path / "tests" / "fixtures" / "citations" / file_name
        files = {"uploaded_file": (open(file_path, mode="rb"), file_path)}
        response = api.post(
            CITATION_IMPORTS_API_ENDPOINT, files=files, **(params or {})
        )
        assert response.status_code == 200

    @pytest.mark.parametrize(
        ["params", "num_exp"],
        [
            ({"review_id": 1}, 2),
        ],
    )
    def test_get(self, params, num_exp, api):
        response = api.get(CITATION_IMPORTS_API_ENDPOINT, **(params or {}))
        assert response.status_code == 200
        data = response.json
        assert data
        assert isinstance(data, list) and len(data) == num_exp
