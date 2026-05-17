import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";

import { getMetrics } from "../services/api";

function formatNumber(value) {
  if (typeof value !== "number") return value ?? "-";
  return Number.isInteger(value) ? value.toString() : value.toFixed(2);
}

function OpsDashboard() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;

    const loadMetrics = async () => {
      try {
        const result = await getMetrics();
        if (!active) return;
        setData(result);
        setError("");
      } catch (loadError) {
        if (!active) return;
        setError(loadError.message || "Unable to load metrics");
      }
      if (active) {
        setLoading(false);
      }
    };

    loadMetrics();
    const intervalId = window.setInterval(loadMetrics, 15000);

    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, []);

  const routeEntries = Object.entries(data?.metrics?.routes || {}).sort(
    (left, right) => right[1].count - left[1].count
  );

  return (
    <div className="page-shell report-page">
      <div className="report-wrap report-wrap-dark">
        <div className="report-hero report-hero-dark good">
          <div>
            <div className="eyebrow">Operations Dashboard</div>
            <h1>Live metrics, cache behavior, and rate limiting.</h1>
            <p>
              This view exposes backend request timings, cache mode, and traffic controls so the
              project reads like an operated full-stack system.
            </p>
          </div>
          <div className="hero-actions">
            <button className="button-secondary" onClick={() => navigate("/")}>
              Back Home
            </button>
            <button className="button-primary" onClick={() => window.location.reload()}>
              Refresh
            </button>
          </div>
        </div>

        {error ? <p className="error-text">{error}</p> : null}
        {loading ? <p className="loading-text">Loading operational metrics...</p> : null}

        {data ? (
          <>
            <div className="report-grid ops-grid">
              <div className="feature-card">
                <h3>Requests</h3>
                <p>Total: {formatNumber(data.metrics?.requests?.total)}</p>
                <p>Errors: {formatNumber(data.metrics?.requests?.errors)}</p>
                <p>Success rate: {formatNumber((data.metrics?.requests?.success_rate || 0) * 100)}%</p>
              </div>
              <div className="feature-card">
                <h3>Cache</h3>
                <p>Backend: {data.cache?.backend || "memory"}</p>
                <p>Hit rate: {formatNumber((data.cache?.hit_rate || 0) * 100)}%</p>
                <p>Items: {formatNumber(data.cache?.size)}</p>
              </div>
              <div className="feature-card">
                <h3>Rate Limit</h3>
                <p>Enabled: {data.rate_limit?.enabled ? "Yes" : "No"}</p>
                <p>Window: {formatNumber(data.rate_limit?.window_seconds)}s</p>
                <p>Max requests: {formatNumber(data.rate_limit?.max_requests)}</p>
              </div>
              <div className="feature-card">
                <h3>Uptime</h3>
                <p>{formatNumber(data.metrics?.uptime_seconds)}s</p>
                <p>Service: {data.service}</p>
                <p>Redis configured: {data.cache?.redis_configured ? "Yes" : "No"}</p>
              </div>
            </div>

            <div className="response-card response-card-dark">
              <div className="response-card-top">
                <div>
                  <div className="eyebrow">Route Timings</div>
                  <h3>Per-route request activity</h3>
                </div>
                <div className="response-meta-pill">
                  {routeEntries.length} route{routeEntries.length === 1 ? "" : "s"}
                </div>
              </div>

              <div className="ops-table">
                <div className="ops-table-head">
                  <span>Route</span>
                  <span>Requests</span>
                  <span>Errors</span>
                  <span>Avg ms</span>
                  <span>Last status</span>
                </div>
                {routeEntries.map(([route, stats]) => (
                  <div key={route} className="ops-table-row">
                    <span>{route}</span>
                    <span>{formatNumber(stats.count)}</span>
                    <span>{formatNumber(stats.errors)}</span>
                    <span>{formatNumber(stats.avg_duration_ms)}</span>
                    <span>{formatNumber(stats.last_status_code)}</span>
                  </div>
                ))}
              </div>
            </div>
          </>
        ) : null}
      </div>
    </div>
  );
}

export default OpsDashboard;
