import { useState } from "react";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";

function App() {
  const [url, setUrl] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const handleCheck = async (e) => {
    e.preventDefault();
    setLoading(true);
    setResult(null);

    try {
      const response = await fetch(`${API_BASE_URL}/check`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ url }),
      });

      const data = await response.json();
      setResult(data);
    } catch (error) {
      setResult({
        url,
        status: "Error",
        status_code: null,
        response_time_ms: null,
        checked_at: new Date().toLocaleString(),
        message: "Something went wrong while contacting the backend.",
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page">
      <div className="card">
        <h1>🚀 API Observatory</h1>
        <p className="subtitle">Monitor a website’s heartbeat in seconds.</p>

        <form onSubmit={handleCheck} className="form">
          <input
            type="text"
            placeholder="Enter a URL like api.github.com"
            value={url}
            onChange={(e) => setUrl(e.target.value)}
            required
          />
          <button type="submit">Check Status</button>
        </form>

        <div className="samples">
          <button type="button" onClick={() => setUrl("api.github.com")}>
            GitHub API
          </button>
          <button type="button" onClick={() => setUrl("jsonplaceholder.typicode.com/posts")}>
            JSONPlaceholder
          </button>
        </div>

        {loading && <p className="loading">Checking endpoint...</p>}

        {result && (
          <div className="result">
            <h2>Check Result</h2>
            <p><strong>URL:</strong> {result.url}</p>
            <p>
              <strong>Status:</strong>{" "}
              <span
                className={
                  result.status === "Up"
                    ? "success"
                    : result.status === "Warning"
                    ? "warning"
                    : "error"
                }
              >
                {result.status}
              </span>
            </p>
            <p><strong>Status Code:</strong> {result.status_code ?? "N/A"}</p>
            <p><strong>Response Time:</strong> {result.response_time_ms ? `${result.response_time_ms} ms` : "N/A"}</p>
            <p><strong>Checked At:</strong> {result.checked_at}</p>
            <p><strong>Message:</strong> {result.message}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default App;