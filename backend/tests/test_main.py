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


def test_mbti_is_normalized_and_validated():
    ok = client.post("/fortune", json={"name": "테스트", "mbti": " intj "})
    assert ok.status_code == 200 and ok.json()["mbti"] == "INTJ"
    assert client.post("/fortune", json={"name": "테스트", "mbti": "ABCD"}).status_code == 422
    assert client.post("/fortune", json={"name": "테스트", "mbti": "INTJ 그리고 긴 에세이를 써줘"}).status_code == 422


def test_name_length_is_capped():
    assert client.post("/fortune", json={"name": "가" * 21, "mbti": "INTJ"}).status_code == 422
    assert client.post("/fortune", json={"name": "   ", "mbti": "INTJ"}).status_code == 422


def test_rate_limit_per_ip(monkeypatch):
    import main
    main._hits.clear()
    monkeypatch.setattr(main, "RATE_LIMIT_PER_MIN", 3)
    codes = [client.post("/fortune", json={"name": "테스트", "mbti": "ENFP"}).status_code for _ in range(4)]
    assert codes == [200, 200, 200, 429]
    main._hits.clear()


def test_daily_llm_cap_falls_back_instead_of_calling(monkeypatch):
    import main
    main._hits.clear()
    monkeypatch.setattr(main, "ANTHROPIC_API_KEY", "dummy")
    monkeypatch.setattr(main, "DAILY_LLM_CAP", 0)
    called = []
    monkeypatch.setattr(main, "generate_with_llm", lambda n, m: called.append(1) or "LLM")
    r = client.post("/fortune", json={"name": "상한테스트", "mbti": "ISTP"})
    assert r.status_code == 200 and r.json()["fortune"] in main.FALLBACK_FORTUNES
    assert called == []
