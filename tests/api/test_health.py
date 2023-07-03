class TestHealthResource:
    def test_get(self, db, client):
        url = "/api/health"
        response = client.get(url)
        assert response.status_code == 200
