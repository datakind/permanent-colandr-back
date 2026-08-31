HEALTH_API_ENDPOINT = "health.health"


class TestHealthAPI:
    def test_get(self, api):
        response = api.get(HEALTH_API_ENDPOINT)
        assert response.status_code == 200
        assert response.json == {"message": "OK"}
