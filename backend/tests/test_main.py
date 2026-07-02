from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_fortune():
    response = client.post("/fortune", json={"name": "테스트", "mbti": "INTJ"})
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "테스트"
    assert data["mbti"] == "INTJ"
    assert isinstance(data["fortune"], str) and len(data["fortune"]) > 0
