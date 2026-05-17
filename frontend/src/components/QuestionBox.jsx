function QuestionBox({ question, loading }) {
  return (
    <div className="question-card">
      <div className="question-avatar">AI</div>
      <div className="question-content">
        <span className="question-label">Interviewer</span>
        <p className="question-text">
          {loading
            ? "The interviewer is preparing your next question..."
            : question || "Press Start Interview to begin."}
        </p>
      </div>
    </div>
  );
}

export default QuestionBox;
