import React from "react";

function ResultCard({ result }) {
  return (
    <div style={{ marginTop: "20px", padding: "15px", border: "1px solid #ccc" }}>
      <h2>📊 Result</h2>

      <p><b>Score:</b> {result.score}</p>
      <p><b>Feedback:</b> {result.feedback}</p>
    </div>
  );
}

export default ResultCard;