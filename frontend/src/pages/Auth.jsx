import { useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import { loginUser, registerUser } from "../services/api";

function Auth() {
  const navigate = useNavigate();
  const location = useLocation();
  const redirectTo = location.state?.redirectTo || "/";
  const [mode, setMode] = useState("login");
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async () => {
    setError("");
    setLoading(true);
    try {
      if (mode === "register") {
        await registerUser({ full_name: fullName, email, password });
      } else {
        await loginUser({ email, password });
      }
      navigate(redirectTo, { replace: true });
    } catch (requestError) {
      setError(
        requestError?.response?.data?.detail ||
          requestError?.message ||
          "Authentication failed. Please try again."
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="page-shell">
      <div className="setup-layout">
        <div className="setup-panel launch-panel">
          <div className="eyebrow">Secure Access</div>
          <h1>{mode === "register" ? "Create your interview account" : "Sign in to continue"}</h1>
          <p>
            Your account keeps interview sessions, saved reports, and launch data scoped to you
            instead of relying on shared local state.
          </p>

          <div className="hero-actions">
            <button
              className={mode === "login" ? "button-primary" : "button-secondary"}
              onClick={() => setMode("login")}
              type="button"
            >
              Sign In
            </button>
            <button
              className={mode === "register" ? "button-primary" : "button-secondary"}
              onClick={() => setMode("register")}
              type="button"
            >
              Create Account
            </button>
          </div>

          {mode === "register" ? (
            <>
              <label>Full Name</label>
              <input
                value={fullName}
                onChange={(event) => setFullName(event.target.value)}
                placeholder="Your name"
              />
            </>
          ) : null}

          <label>Email</label>
          <input
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            placeholder="you@example.com"
            type="email"
          />

          <label>Password</label>
          <input
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="At least 8 characters"
            type="password"
          />

          {error ? <p className="error-text">{error}</p> : null}

          <div className="hero-actions">
            <button className="button-primary" onClick={submit} disabled={loading}>
              {loading
                ? "Working..."
                : mode === "register"
                  ? "Create Account"
                  : "Sign In"}
            </button>
          </div>
        </div>

        <aside className="setup-sidecard">
          <div className="eyebrow">What changes</div>
          <h2>Production-style access and persistence</h2>
          <div className="setup-checklist">
            <div>1. Each user gets their own interview sessions and report history.</div>
            <div>2. The backend now protects routes with bearer-token authentication.</div>
            <div>3. Sessions and reports survive backend restarts in the database.</div>
            <div>4. This is much closer to a real launchable product than shared local memory.</div>
          </div>
        </aside>
      </div>
    </div>
  );
}

export default Auth;
