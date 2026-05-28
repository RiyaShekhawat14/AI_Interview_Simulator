import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { checkHealth, getCurrentUser, getSavedReports, isAuthenticated, logoutUser } from "../services/api";

function Home() {
  const navigate = useNavigate();
  const [health, setHealth] = useState({
    backend: false,
    ollama: false,
    loading: true,
  });
  const [user, setUser] = useState(null);
  const [reports, setReports] = useState([]);

  useEffect(() => {
    let active = true;
    const loadHealth = async () => {
      try {
        const result = await checkHealth();
        if (!active) return;
        setHealth({ ...result, loading: false });
      } catch (error) {
        if (!active) return;
        setHealth({ backend: false, ollama: false, loading: false, error: error.message });
      }
    };
    const loadUserContext = async () => {
      if (!isAuthenticated()) {
        return;
      }
      try {
        const [{ user: activeUser }, reportData] = await Promise.all([
          getCurrentUser(),
          getSavedReports(3),
        ]);
        if (!active) return;
        setUser(activeUser);
        setReports(reportData?.reports || []);
      } catch {
        if (!active) return;
        logoutUser();
        setUser(null);
        setReports([]);
      }
    };
    loadHealth();
    loadUserContext();
    return () => {
      active = false;
    };
  }, []);

  return (
    <div className="page-shell">
      <div className="home-container">
        <div className="hero-card hero-card-large">
          <div className="hero-copy">
            <div className="eyebrow hero-eyebrow">Launch-ready mock interviews</div>
            <h1 className="page-title">AI interview practice with live voice, camera, DSA, and feedback.</h1>
            <p className="page-subtitle">
              Simulate a real hiring flow with resume-aware questions, a persistent side camera,
              spoken prompts, typed or voice answers, a coding round, and a final report built
              for actual interview improvement.
            </p>

            <div className="hero-actions">
              {user ? (
                <>
                  <button className="button-primary" onClick={() => navigate("/setup")}>
                    Launch Interview
                  </button>
                  <button className="button-secondary" onClick={() => navigate("/report")}>
                    Open Last Report
                  </button>
                  <button className="button-secondary" onClick={() => navigate("/ops")}>
                    Open Ops Dashboard
                  </button>
                  <button
                    className="button-secondary"
                    onClick={() => {
                      logoutUser();
                      setUser(null);
                      setReports([]);
                      navigate("/auth");
                    }}
                  >
                    Sign Out
                  </button>
                </>
              ) : (
                <>
                  <button className="button-primary" onClick={() => navigate("/auth?mode=login")}>
                    Sign In To Start
                  </button>
                  <button className="button-secondary" onClick={() => navigate("/auth?mode=register")}>
                    Create Account
                  </button>
                </>
              )}
            </div>
          </div>

          <div className="hero-sidecard">
            <div className="hero-sidecard-header">
              <span>System readiness</span>
              <strong>{health.loading ? "Checking..." : "Live status"}</strong>
            </div>

            <div className="health-list">
              <div className={`health-item ${health.backend ? "healthy" : "offline"}`}>
                <span>Backend API</span>
                <strong>{health.backend ? "Online" : "Offline"}</strong>
              </div>
              <div className={`health-item ${health.ollama ? "healthy" : "warning"}`}>
                <span>Ollama</span>
                <strong>{health.ollama ? "Connected" : "Fallback mode"}</strong>
              </div>
              <div className="health-item neutral">
                <span>Model</span>
                <strong>{health.ollama_model || "llama3:8b"}</strong>
              </div>
            </div>

            <p className="hero-status-note">
              {health.ollama
                ? `Questions are currently coming from ${health.ollama_model || "Ollama"}.`
                : "If Ollama is unavailable, the app still runs with fallback questions and local report logic."}
            </p>
            <p className="hero-status-note">
              {user
                ? `Signed in as ${user.full_name} with ${reports.length} recent report${reports.length === 1 ? "" : "s"}.`
                : "Sign in to unlock persistent sessions and saved report history."}
            </p>
          </div>
        </div>

        <div className="features">
          <div className="feature-card">
            <h3>Resume-aware AI interviewer</h3>
            <p>Role, company, and resume context guide the question flow instead of generic prompts.</p>
          </div>

          <div className="feature-card">
            <h3>Voice and text answers</h3>
            <p>Users can speak, type, or combine both, while the interviewer responds in chatbot style.</p>
          </div>

          <div className="feature-card">
            <h3>Side camera emotion tracking</h3>
            <p>A persistent live camera view keeps emotion detection visible through the full interview.</p>
          </div>

          <div className="feature-card">
            <h3>DSA round with IDE feel</h3>
            <p>After the general round, the experience shifts into a coding workspace with language selection.</p>
          </div>

          <div className="feature-card">
            <h3>Secure account-backed progress</h3>
            <p>Users now sign in with their own account, and sessions plus reports are stored per user.</p>
          </div>
        </div>

        <footer className="footer">
          <p>Copyright 2026 Interview Labs. Built for serious launch-quality mock interviews.</p>
        </footer>
      </div>
    </div>
  );
}

export default Home;
