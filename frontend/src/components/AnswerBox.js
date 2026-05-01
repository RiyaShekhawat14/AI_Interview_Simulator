import React from "react";

function AnswerBox({ answer, setAnswer }) {
  return (
    <div style={{ marginTop: "20px" }}>
      <h3>Your Answer</h3>

      <textarea
        rows="5"
        placeholder="Type your answer here..."
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
        style={{ width: "100%", padding: "10px" }}
      />
    </div>
  );
}

export default AnswerBox;