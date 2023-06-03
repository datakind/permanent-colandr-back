def test_get_index(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.data
