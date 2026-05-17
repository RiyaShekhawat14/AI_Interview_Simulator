function AnswerBox({ answer, setAnswer }) {
  return (
    <div className="input-group">
      <h3>Your Answer</h3>
      <textarea
        placeholder="Type your answer here..."
        value={answer}
        onChange={(e) => setAnswer(e.target.value)}
      />
    </div>
  );
}

export default AnswerBox;
