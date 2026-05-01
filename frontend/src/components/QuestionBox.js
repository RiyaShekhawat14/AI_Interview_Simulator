import React from "react";

function QuestionBox({ question }) {
  return (
    <div style={{ marginTop: "20px" }}>
      <h2>Question:</h2>
      <p>{question}</p>
    </div>
  );
}

export default QuestionBox;