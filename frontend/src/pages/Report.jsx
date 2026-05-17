import { useEffect, useState } from "react";
import { motion } from "framer-motion";
import { useLocation, useNavigate } from "react-router-dom";
import { getLatestReport } from "../services/api";

function Report() {
  const location = useLocation();
  const navigate = useNavigate();
  const [data, setData] = useState(
    location.state || JSON.parse(localStorage.getItem("report") || "null")
  );
  const [activeIndex, setActiveIndex] = useState(0);
  const [loading, setLoading] = useState(false);
  const report = data || {};
  const {
    overall_score = 0,
    assessment = "",
    emotion_summary = "",
    confidence_report = "",
    communication_report = "",
    strengths = [],
    weaknesses = [],
    recommendations = [],
    responses = [],
    response_count = 0,
    code_challenges_completed = 0,
    duration_seconds = 0,
    role = "",
    company = "",
  } = report;
  const activeResponse = responses[activeIndex] || null;
  const scoreTone =
    overall_score >= 80 ? "excellent" : overall_score >= 60 ? "good" : "needs-work";
  const scoreLabel =
    overall_score >= 80
      ? "Interview Ready"
      : overall_score >= 60
        ? "Strong Progress"
        : "Needs More Practice";
  const nextFocus =
    recommendations[0] ||
    weaknesses[0] ||
    "Keep practicing concise, structured answers with clear problem solving.";
  const responseTypeLabel =
    activeResponse?.phase === "dsa" ? "Code Challenge" : "Behavioral Round";

  useEffect(() => {
    if (data) {
      return;
    }

    let active = true;
    const loadLatestReport = async () => {
      setLoading(true);
      try {
        const latest = await getLatestReport();
        if (!active) return;
        const latestReport = latest?.report || null;
        if (latestReport) {
          localStorage.setItem("report", JSON.stringify(latestReport));
          setData(latestReport);
        }
      } catch {
        if (!active) return;
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    };

    loadLatestReport();
    return () => {
      active = false;
    };
  }, [data]);

  const downloadReport = () => {
    const reportData = JSON.stringify(data, null, 2);
    const blob = new Blob([reportData], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "interview-report.json";
    link.click();
    URL.revokeObjectURL(url);
  };

  if (!data) {
    return (
      <div className="page-shell report-page">
        <div className="setup-panel">
          <h2>No Report Available</h2>
          <p>
            {loading
              ? "Loading your latest saved interview report..."
              : "Complete an interview first so the AI can generate your review."}
          </p>
          <button className="button-primary" onClick={() => navigate("/")}>
            Go Home
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="page-shell report-page">
      <div className="report-wrap report-wrap-dark">
        <motion.div
          className={`report-hero report-hero-dark ${scoreTone}`}
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45 }}
        >
          <div>
            <div className="eyebrow">Final Interview Report</div>
            <h1>{role} Interview Review</h1>
            <p>{company ? `Target company: ${company}` : assessment}</p>
            <div className="report-hero-tags">
              <span className="report-pill">{scoreLabel}</span>
              <span className="report-pill report-pill-muted">
                {response_count} reviewed responses
              </span>
            </div>
          </div>
          <div className="score-badge score-badge-dark">
            <span>Overall Score</span>
            <strong>{overall_score}/100</strong>
            <small>{scoreLabel}</small>
          </div>
        </motion.div>

        <motion.div
          className="report-grid"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.08 }}
        >
          <div className="stat-card stat-card-dark">
            <h3>Assessment</h3>
            <p>{assessment}</p>
          </div>
          <div className="stat-card stat-card-dark">
            <h3>Emotion Summary</h3>
            <p>{emotion_summary}</p>
          </div>
          <div className="stat-card stat-card-dark">
            <h3>Confidence Report</h3>
            <p>{confidence_report}</p>
          </div>
          <div className="stat-card stat-card-dark">
            <h3>Communication Report</h3>
            <p>{communication_report}</p>
          </div>
        </motion.div>

        <motion.div
          className="camera-stats report-metrics"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.14 }}
        >
          <div className="stat-tile stat-tile-dark">
            <span>Responses</span>
            <strong>{response_count}</strong>
          </div>
          <div className="stat-tile stat-tile-dark">
            <span>DSA Answers</span>
            <strong>{code_challenges_completed}</strong>
          </div>
          <div className="stat-tile stat-tile-dark">
            <span>Duration</span>
            <strong>{duration_seconds}s</strong>
          </div>
        </motion.div>

        <motion.div
          className="feedback-sections"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.2 }}
        >
          <div className="feedback-card feedback-card-dark">
            <h3>Strengths</h3>
            <ul>
              {strengths.map((item, index) => (
                <li key={`strength-${index}`}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="feedback-card feedback-card-dark">
            <h3>Weaknesses</h3>
            <ul>
              {weaknesses.map((item, index) => (
                <li key={`weakness-${index}`}>{item}</li>
              ))}
            </ul>
          </div>
          <div className="feedback-card feedback-card-dark">
            <h3>Recommendations</h3>
            <ul>
              {recommendations.map((item, index) => (
                <li key={`recommendation-${index}`}>{item}</li>
              ))}
            </ul>
          </div>
        </motion.div>

        <motion.div
          className="report-focus-band"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.23 }}
        >
          <div className="report-focus-card">
            <span className="eyebrow">Next Focus</span>
            <p>{nextFocus}</p>
          </div>
        </motion.div>

        <motion.div
          className="response-section response-section-dark"
          initial={{ opacity: 0, y: 18 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.45, delay: 0.26 }}
        >
          <div className="report-section-header">
            <div>
              <h2>Question-by-Question Review</h2>
              <p>Select any response to inspect the AI-corrected answer or solution.</p>
            </div>
          </div>

          <div className="response-review-grid">
            <div className="response-selector-list">
              {responses.map((response, index) => (
                <button
                  key={`response-selector-${index}`}
                  type="button"
                  className={`response-selector ${index === activeIndex ? "active" : ""}`}
                  onClick={() => setActiveIndex(index)}
                >
                  <span>{response.phase === "dsa" ? "DSA" : "Interview"}</span>
                  <strong>Q{index + 1}</strong>
                  <small>{response.score}/100</small>
                </button>
              ))}
            </div>

            {activeResponse ? (
              <motion.article
                key={`active-response-${activeIndex}`}
                className="response-card response-card-dark response-card-spotlight"
                initial={{ opacity: 0, y: 12 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.28 }}
              >
                <div className="response-card-top">
                  <div>
                    <span className="response-phase">
                      {activeResponse.phase === "dsa" ? "DSA Round" : "Interview Round"}
                    </span>
                    <h3>Q{activeIndex + 1}. {activeResponse.question}</h3>
                  </div>
                  <div className="response-score">{activeResponse.score}/100</div>
                </div>

                <div className="response-meta">
                  <span className="response-meta-pill">{responseTypeLabel}</span>
                  <span>Emotion: {activeResponse.emotion}</span>
                  <span>Emotion Confidence: {Math.round((activeResponse.emotion_confidence || 0) * 100)}%</span>
                  {activeResponse.language ? <span>Language: {activeResponse.language}</span> : null}
                </div>

                <div className="response-block">
                  <strong>Your Answer</strong>
                  {activeResponse.phase === "dsa" ? (
                    <pre className="report-code-block">{activeResponse.answer}</pre>
                  ) : (
                    <p>{activeResponse.answer}</p>
                  )}
                </div>

                <div className="response-block">
                  <strong>Feedback</strong>
                  <p>{activeResponse.feedback}</p>
                </div>

                <div className="response-block">
                  <strong>Improvement</strong>
                  <p>{activeResponse.improvement}</p>
                </div>

                {activeResponse.phase === "dsa" && activeResponse.corrected_code ? (
                  <div className="response-block corrected corrected-code">
                    <strong>Corrected Solution</strong>
                    <pre className="report-code-block">{activeResponse.corrected_code}</pre>
                  </div>
                ) : null}

                <div className="response-block corrected">
                  <strong>{activeResponse.phase === "dsa" ? "Corrected Explanation" : "Corrected Answer"}</strong>
                  <p>{activeResponse.corrected_answer}</p>
                </div>
              </motion.article>
            ) : null}
          </div>
        </motion.div>

        <div className="action-row">
          <button className="button-primary" onClick={downloadReport}>
            Download Report
          </button>
          <button className="button-secondary" onClick={() => navigate("/setup")}>
            Try Another Interview
          </button>
        </div>
      </div>
    </div>
  );
}

export default Report;
