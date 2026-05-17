import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { checkHealth, uploadResume } from "../services/api";

function Setup() {
  const navigate = useNavigate();
  const [role, setRole] = useState("");
  const [company, setCompany] = useState("");
  const [resume, setResume] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [health, setHealth] = useState({
    backend: false,
    ollama: false,
    loading: true,
  });

  useEffect(() => {
    let active = true;
    const loadHealth = async () => {
      try {
        const result = await checkHealth();
        if (!active) return;
        setHealth({ ...result, loading: false });
      } catch (healthError) {
        if (!active) return;
        setHealth({ backend: false, ollama: false, loading: false, error: healthError.message });
      }
    };

    loadHealth();
    return () => {
      active = false;
    };
  }, []);

  const handleStart = async () => {
    if (!role.trim() || !company.trim() || !resume) {
      setError("Please add role, company and resume PDF.");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const uploadResult = await uploadResume(resume);
      const resumeText = uploadResult.text;
      localStorage.setItem("resumeText", resumeText);

      navigate("/interview", {
        state: {
          role: role.trim(),
          company: company.trim(),
          resumeText,
        },
      });
    } catch (err) {
      let backendMessage = "Could not upload resume. Please try again.";

      if (err?.response?.data?.detail) {
        backendMessage = err.response.data.detail;
      } else if (err?.message) {
        backendMessage = err.message;
      }

      if (backendMessage.includes("Network Error") || backendMessage.includes("timeout")) {
        backendMessage =
          "Unable to reach the backend server. Make sure the backend is running at http://localhost:8000 and refresh the page.";
      }

      setError(backendMessage);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="setup-layout">
        <div className="setup-panel launch-panel">
          <div className="eyebrow">Interview configuration</div>
          <h1>Prepare a launch-quality interview session</h1>
          <p>
            Choose the target company and role, upload a resume, and start a guided
            AI interview with voice, camera, DSA mode, and a final coaching report.
          </p>

          <label>Company</label>
          <input
            value={company}
            onChange={(e) => setCompany(e.target.value)}
            placeholder="e.g. Google"
          />

          <label>Role</label>
          <input
            value={role}
            onChange={(e) => setRole(e.target.value)}
            placeholder="e.g. Software Engineer"
          />

          <label>Resume (PDF)</label>
          <input
            type="file"
            accept=".pdf"
            onChange={(e) => setResume(e.target.files?.[0] || null)}
          />

          {error ? <p className="error-text">{error}</p> : null}

          <div className="hero-actions">
            <button className="button-primary" onClick={handleStart} disabled={loading}>
              {loading ? "Preparing..." : "Start Interview"}
            </button>
          </div>
        </div>

        <aside className="setup-sidecard">
          <div className="eyebrow">Live health</div>
          <h2>System status before launch</h2>

          <div className="health-list">
            <div className={`health-item ${health.backend ? "healthy" : "offline"}`}>
              <span>Backend</span>
              <strong>{health.loading ? "Checking..." : health.backend ? "Online" : "Offline"}</strong>
            </div>
            <div className={`health-item ${health.ollama ? "healthy" : "warning"}`}>
              <span>Ollama</span>
              <strong>{health.loading ? "Checking..." : health.ollama ? "Connected" : "Fallback mode"}</strong>
            </div>
            <div className="health-item neutral">
              <span>Question source</span>
              <strong>{health.ollama ? "Live model responses" : "Fallback questions available"}</strong>
            </div>
          </div>

          <div className="setup-checklist">
            <div>1. Resume upload unlocks resume-aware questions.</div>
            <div>2. The interview begins in chatbot mode with camera tracking on the side.</div>
            <div>3. After 5 questions, the interface moves into the DSA coding round.</div>
            <div>4. Stopping the interview generates the final emotion and improvement report.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default Setup;
