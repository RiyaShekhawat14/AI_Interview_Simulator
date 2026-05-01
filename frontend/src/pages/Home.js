import React from "react";
import { useNavigate } from "react-router-dom";

function Home() {
  const navigate = useNavigate();

  return (
    <div style={{ textAlign: "center", marginTop: "100px" }}>
      <h1>🎤 AI Interview Simulator</h1>

      <button onClick={() => navigate("/interview")}>
        Start Interview
      </button>
    </div>
  );
}

export default Home;