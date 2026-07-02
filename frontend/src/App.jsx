import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export default function App() {
  const [name, setName] = useState("");
  const [mbti, setMbti] = useState("");
  const [fortune, setFortune] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    setFortune("");
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE_URL}/fortune`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, mbti }),
      });
      if (!res.ok) throw new Error(`요청 실패: ${res.status}`);
      const data = await res.json();
      setFortune(data.fortune);
    } catch (err) {
      setError(err.message || "오류가 발생했습니다.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "60px auto", fontFamily: "sans-serif" }}>
      <h1>오늘의 운세 🔮</h1>
      <form onSubmit={handleSubmit}>
        <div style={{ marginBottom: 12 }}>
          <label>이름</label>
          <br />
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label>MBTI</label>
          <br />
          <input
            value={mbti}
            onChange={(e) => setMbti(e.target.value.toUpperCase())}
            placeholder="예: INTJ"
            maxLength={4}
            required
            style={{ width: "100%", padding: 8 }}
          />
        </div>
        <button type="submit" disabled={loading} style={{ padding: "8px 16px" }}>
          {loading ? "운세 보는 중..." : "오늘의 운세 보기"}
        </button>
      </form>

      {error && <p style={{ color: "red" }}>{error}</p>}
      {fortune && (
        <div style={{ marginTop: 24, padding: 16, background: "#f5f5f5", borderRadius: 8 }}>
          <p>{fortune}</p>
        </div>
      )}
    </div>
  );
}
