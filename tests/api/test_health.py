import flask


HEALTH_API_ENDPOINT = "health.health"


class TestHealthAPI:
    def test_get(self, app, client):
        with app.test_request_context():
            url = flask.url_for(HEALTH_API_ENDPOINT, id=id)
        response = client.get(url, headers=None)
        assert response.status_code == 200
        assert response.json == {"message": "OK"}
