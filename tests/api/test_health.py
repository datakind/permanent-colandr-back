class TestHealthResource:
    def test_get(self, client):
        url = "/api/health"
        response = client.get(url)
        assert response.status_code == 200
        assert response.json == "OK"
