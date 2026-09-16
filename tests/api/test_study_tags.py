import pytest


STUDY_TAGS_API_ENDPOINT = "study_tags.study_tags"


@pytest.mark.usefixtures("db_session")
class TestStudyTagsAPI:
    @pytest.mark.parametrize(
        ["params", "status_code", "exp_result"],
        [
            ({"review_id": 1}, 200, ["TAG1", "TAG2", "TAG3"]),
            ({"review_id": 2}, 200, ["TAG4"]),
            ({"review_id": 999}, 404, None),
        ],
    )
    def test_get(self, params, status_code, exp_result, api):
        response = api.get(STUDY_TAGS_API_ENDPOINT, **params)
        assert response.status_code == status_code
        if 200 <= status_code < 300:
            data = response.json
            assert isinstance(data, list)
            assert data == exp_result
