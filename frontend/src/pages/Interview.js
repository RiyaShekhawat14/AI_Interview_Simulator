import React, { useState } from "react";
import axios from "axios";

import CompanyDropdown from "../components/CompanyDropdown";
import RoleInput from "../components/RoleInput";
import QuestionBox from "../components/QuestionBox";
import AnswerBox from "../components/AnswerBox";
import ResultCard from "../components/ResultCard";
import AudioRecorder from "../components/AudioRecorder";

function Interview() {
  const [company, setCompany] = useState("");
  const [role, setRole] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [result, setResult] = useState(null);
  const [audioBlob, setAudioBlob] = useState(null);

  const getQuestion = async () => {
    const res = await axios.post(
      "http://127.0.0.1:8000/question?role=" + role + "&company=" + company
    );
    setQuestion(res.data.question);
  };

  const submitAnswer = async () => {
    const res = await axios.post(
      "http://127.0.0.1:8000/evaluate?answer=" + answer
    );
    setResult(res.data);
  };

  return (
    <div style={{ padding: "20px" }}>
      <h1>Interview</h1>

      <CompanyDropdown setCompany={setCompany} />
      <RoleInput role={role} setRole={setRole} />

      <button onClick={getQuestion}>Start</button>

      {question && <QuestionBox question={question} />}

      {question && (
        <>
          <AnswerBox answer={answer} setAnswer={setAnswer} />
          <AudioRecorder setAudioBlob={setAudioBlob} />
          <button onClick={submitAnswer}>Submit</button>
        </>
      )}

      {result && <ResultCard result={result} />}
    </div>
  );
}

export default Interview;