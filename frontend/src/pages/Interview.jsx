import { useEffect, useRef, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";

import {
  checkHealth,
  detectEmotion,
  getInterviewReport,
  getNextInterviewQuestion,
  startInterviewSession,
  submitCodeAnswer,
} from "../services/api";
import "../App.css";

const CAMERA_SAMPLE_INTERVAL_MS = 3500;
const GENERAL_QUESTION_LIMIT = 5;

function resolveInterviewPhase(step) {
  if (step?.type === "code") {
    return "dsa";
  }
  if (step?.phase) {
    return step.phase;
  }
  if ((step?.general_questions_completed || 0) >= GENERAL_QUESTION_LIMIT) {
    return "dsa";
  }
  return "general";
}

function Interview() {
  const location = useLocation();
  const navigate = useNavigate();
  const { role = "", company = "", resumeText = "" } = location.state || {};

  const [messages, setMessages] = useState([
    { type: "system", text: "Preparing your AI interviewer..." },
  ]);
  const [answer, setAnswer] = useState("");
  const [codeAnswer, setCodeAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const [listening, setListening] = useState(false);
  const [sessionId, setSessionId] = useState("");
  const [currentQuestion, setCurrentQuestion] = useState("");
  const [currentPhase, setCurrentPhase] = useState("general");
  const [currentLanguage, setCurrentLanguage] = useState("python");
  const [questionCount, setQuestionCount] = useState(0);
  const [currentEmotion, setCurrentEmotion] = useState("Normal");
  const [currentEmotionConfidence, setCurrentEmotionConfidence] = useState(0);
  const [emotionStatus, setEmotionStatus] = useState("Starting camera...");
  const [isCameraReady, setIsCameraReady] = useState(false);
  const [questionSource, setQuestionSource] = useState("fallback");
  const [questionModel, setQuestionModel] = useState("");
  const [liveHealth, setLiveHealth] = useState({ backend: true, ollama: false });
  const [voiceSupported, setVoiceSupported] = useState(() => !!window.speechSynthesis);
  const [speechSupported] = useState(
    () => !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  );

  const videoRef = useRef(null);
  const canvasRef = useRef(null);
  const chatAreaRef = useRef(null);
  const composerRef = useRef(null);
  const recognitionRef = useRef(null);
  const cameraStreamRef = useRef(null);
  const emotionLoopRef = useRef(null);
  const emotionBusyRef = useRef(false);
  const loadingRef = useRef(false);
  const phaseRef = useRef("general");
  const autoVoiceEnabledRef = useRef(false);
  const languageOptions = [
    { value: "python", label: "Python", extension: "py" },
    { value: "javascript", label: "JavaScript", extension: "js" },
    { value: "typescript", label: "TypeScript", extension: "ts" },
    { value: "java", label: "Java", extension: "java" },
    { value: "cpp", label: "C++", extension: "cpp" },
    { value: "csharp", label: "C#", extension: "cs" },
    { value: "go", label: "Go", extension: "go" },
    { value: "rust", label: "Rust", extension: "rs" },
  ];

  function applyInterviewStep(step) {
    const resolvedPhase = resolveInterviewPhase(step);
    setCurrentQuestion(step.question || "");
    setCurrentPhase(resolvedPhase);
    setCurrentLanguage(step.language || "python");
    setQuestionCount(step.question_number || 1);
    setQuestionSource(step.question_source || "fallback");
    setQuestionModel(step.question_model || "");
  }

  async function refreshHealth() {
    try {
      const status = await checkHealth();
      setLiveHealth(status);
    } catch (error) {
      setLiveHealth({ backend: false, ollama: false, error: error.message });
    }
  }

  async function startCamera() {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true });
      cameraStreamRef.current = stream;
      if (videoRef.current) {
        videoRef.current.srcObject = stream;
      }
      setIsCameraReady(true);
      setEmotionStatus("Camera active. Tracking interview emotion...");
      startEmotionLoop();
    } catch (error) {
      console.error("Could not access webcam:", error);
      setEmotionStatus("Camera access failed. Emotion tracking unavailable.");
    }
  }

  function stopCamera() {
    if (emotionLoopRef.current) {
      clearInterval(emotionLoopRef.current);
      emotionLoopRef.current = null;
    }
    if (cameraStreamRef.current) {
      cameraStreamRef.current.getTracks().forEach((track) => track.stop());
      cameraStreamRef.current = null;
    }
  }

  function startEmotionLoop() {
    if (emotionLoopRef.current) {
      clearInterval(emotionLoopRef.current);
    }
    emotionLoopRef.current = setInterval(() => {
      captureEmotionSnapshot();
    }, CAMERA_SAMPLE_INTERVAL_MS);
  }

  function captureFrameBlob() {
    return new Promise((resolve) => {
      const video = videoRef.current;
      const canvas = canvasRef.current;
      if (!video || !canvas || !video.videoWidth) {
        resolve(null);
        return;
      }

      canvas.width = video.videoWidth;
      canvas.height = video.videoHeight;
      const context = canvas.getContext("2d");
      context.drawImage(video, 0, 0);
      canvas.toBlob((blob) => resolve(blob), "image/jpeg", 0.9);
    });
  }

  function getVoice() {
    const voices = window.speechSynthesis?.getVoices() || [];
    return (
      voices.find((voice) => voice.lang?.toLowerCase().startsWith("en")) ||
      voices[0] ||
      null
    );
  }

  function getCurrentLanguageExtension() {
    return (
      languageOptions.find((option) => option.value === currentLanguage)?.extension || "txt"
    );
  }

  function stopVoiceInput(disableAutoRestart = true) {
    if (disableAutoRestart) {
      autoVoiceEnabledRef.current = false;
    }
    recognitionRef.current?.stop?.();
  }

  function speak(text, resumeVoiceCapture = false) {
    if (!window.speechSynthesis || !text) return;

    stopVoiceInput(!resumeVoiceCapture);
    window.speechSynthesis.cancel();
    const speech = new SpeechSynthesisUtterance(text);
    const voice = getVoice();
    if (voice) {
      speech.voice = voice;
    }
    speech.rate = 0.95;
    speech.pitch = 1;
    speech.volume = 1;
    speech.lang = "en-US";
    speech.onend = () => {
      if (resumeVoiceCapture && speechSupported && phaseRef.current === "general") {
        startVoiceInput(true);
      }
    };
    window.speechSynthesis.speak(speech);
  }

  async function captureEmotionSnapshot() {
    if (!isCameraReady || emotionBusyRef.current) return;

    emotionBusyRef.current = true;
    try {
      const blob = await captureFrameBlob();
      if (!blob) return;

      const result = await detectEmotion(blob);
      setCurrentEmotion(result?.emotion || "Normal");
      setCurrentEmotionConfidence(result?.confidence || 0);
      setEmotionStatus(result?.status || "tracking");
    } catch (error) {
      console.warn("Emotion detection failed:", error);
      setEmotionStatus("emotion_detection_failed");
    } finally {
      emotionBusyRef.current = false;
    }
  }

  async function beginInterview() {
    setLoading(true);
    try {
      const storedResumeText =
        resumeText || location.state?.resumeText || localStorage.getItem("resumeText") || "";
      const session = await startInterviewSession(role, company, storedResumeText);
      setSessionId(session.session_id);

      const firstQuestion = await getNextInterviewQuestion(
        session.session_id,
        "",
        currentEmotion,
        currentEmotionConfidence
      );

      if (firstQuestion.phase === "complete" || !firstQuestion.question) {
        throw new Error("Interview session did not return an opening question.");
      }

      applyInterviewStep(firstQuestion);
      setMessages([{ type: "ai", text: firstQuestion.question }]);
      speak(firstQuestion.question, true);
    } catch (error) {
      console.error("Error starting interview:", error);
      const fallback = "Tell me about yourself and your recent experience.";
      setCurrentQuestion(fallback);
      setMessages([{ type: "ai", text: fallback }]);
      speak(fallback, true);
    } finally {
      setLoading(false);
    }
  }

  function startVoiceInput(autoRestart = false) {
    window.speechSynthesis?.cancel();

    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SpeechRecognition) {
      return;
    }

    autoVoiceEnabledRef.current = autoRestart;
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // Ignore stop errors from stale recognition instances.
      }
    }

    const recognition = new SpeechRecognition();
    recognition.lang = "en-US";
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    recognition.continuous = false;
    recognitionRef.current = recognition;

    recognition.onstart = () => setListening(true);
    recognition.onend = () => {
      setListening(false);
      if (
        autoVoiceEnabledRef.current &&
        phaseRef.current === "general" &&
        !loadingRef.current
      ) {
        window.setTimeout(() => {
          if (autoVoiceEnabledRef.current && phaseRef.current === "general") {
            startVoiceInput(true);
          }
        }, 400);
      }
    };
    recognition.onerror = () => setListening(false);
    recognition.onresult = (event) => {
      let transcript = "";
      for (let index = event.resultIndex; index < event.results.length; index += 1) {
        if (event.results[index].isFinal) {
          transcript += `${event.results[index][0].transcript} `;
        }
      }
      if (transcript) {
        setAnswer((previous) => `${previous} ${transcript}`.trim());
      }
    };

    try {
      recognition.start();
    } catch (error) {
      console.error("Speech recognition failed to start:", error);
      setListening(false);
    }
  }

  async function advanceInterview() {
    if (!sessionId || !currentQuestion) return;

    setLoading(true);
    try {
      await captureEmotionSnapshot();

      if (currentPhase === "dsa") {
        const code = codeAnswer.trim();
        if (!code) {
          setLoading(false);
          return;
        }

        const evaluation = await submitCodeAnswer(
          sessionId,
          code,
          currentLanguage,
          currentEmotion,
          currentEmotionConfidence
        );
        if (evaluation?.error) {
          throw new Error(evaluation.error);
        }
        setMessages((previous) => [
          ...previous,
          { type: "code", text: code, language: currentLanguage },
        ]);
        setCodeAnswer("");
      } else {
        const textAnswer = answer.trim();
        if (!textAnswer) {
          setLoading(false);
          return;
        }

        setMessages((previous) => [...previous, { type: "user", text: textAnswer }]);
      }

      const submittedAnswer = currentPhase === "dsa" ? "" : answer.trim();
      if (currentPhase !== "dsa") {
        setAnswer("");
      }

      const next = await getNextInterviewQuestion(
        sessionId,
        submittedAnswer,
        currentEmotion,
        currentEmotionConfidence
      );
      await refreshHealth();

      if (next.phase === "complete" || !next.question) {
        const report = await getInterviewReport(sessionId);
        localStorage.setItem("report", JSON.stringify(report));
        navigate("/report", { state: report });
        return;
      }

      applyInterviewStep({ ...next, language: next.language || currentLanguage });
      setMessages((previous) => [...previous, { type: "ai", text: next.question }]);
      speak(next.question, resolveInterviewPhase(next) === "general");
    } catch (error) {
      console.error("Error advancing interview:", error);
      setMessages((previous) => [
        ...previous,
        {
          type: "meta",
          text: "The interviewer hit an issue. Try Next again or stop and generate the report.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  async function stopInterview() {
    if (!sessionId) return;

    setLoading(true);
    try {
      stopVoiceInput();
      const pendingText = answer.trim();
      const pendingCode = codeAnswer.trim();

      await captureEmotionSnapshot();

      if (currentPhase === "dsa" && pendingCode) {
        const evaluation = await submitCodeAnswer(
          sessionId,
          pendingCode,
          currentLanguage,
          currentEmotion,
          currentEmotionConfidence
        );
        if (evaluation?.error) {
          throw new Error(evaluation.error);
        }
      } else if (currentPhase !== "dsa" && pendingText) {
        await getNextInterviewQuestion(
          sessionId,
          pendingText,
          currentEmotion,
          currentEmotionConfidence
        );
      }

      const report = await getInterviewReport(sessionId);
      localStorage.setItem("report", JSON.stringify(report));
      navigate("/report", { state: report });
    } catch (error) {
      console.error("Error stopping interview:", error);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    loadingRef.current = loading;
  }, [loading]);

  useEffect(() => {
    phaseRef.current = currentPhase;
  }, [currentPhase]);

  useEffect(() => {
    const intervalId = window.setInterval(() => {
      refreshHealth();
    }, 10000);

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        refreshHealth();
      }
    };

    document.addEventListener("visibilitychange", handleVisibilityChange);

    return () => {
      window.clearInterval(intervalId);
      document.removeEventListener("visibilitychange", handleVisibilityChange);
    };
  }, []);

  useEffect(() => {
    const chatArea = chatAreaRef.current;
    if (!chatArea) return;
    chatArea.scrollTop = chatArea.scrollHeight;
  }, [messages, loading]);

  useEffect(() => {
    if (currentPhase !== "dsa") return;
    composerRef.current?.scrollIntoView?.({ behavior: "smooth", block: "nearest" });
  }, [currentPhase, currentQuestion]);

  useEffect(() => {
    if (!role || !company) {
      navigate("/setup");
      return;
    }

    let active = true;

    const initialize = async () => {
      await refreshHealth();
      await startCamera();
      if (!active) return;
      await beginInterview();
    };

    initialize();

    if (window.speechSynthesis) {
      window.speechSynthesis.getVoices();
      window.speechSynthesis.onvoiceschanged = () => {
        setVoiceSupported(
          !!window.speechSynthesis && window.speechSynthesis.getVoices().length > 0
        );
      };
    }

    return () => {
      active = false;
      autoVoiceEnabledRef.current = false;
      stopCamera();
      window.speechSynthesis?.cancel();
      recognitionRef.current?.stop?.();
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div className="interview-page">
      <div className="interview-frame">
        <div className="interview-topbar">
          <div className="topbar-copy">
            <div className="eyebrow">Interview Workspace</div>
            <h1>{role} Interview Simulation</h1>
            <p>{company} focused mock interview with live camera, voice support, and report generation.</p>
          </div>
        </div>
        <div className="interview-shell">
          <div className="interview-main-row">
            <section className="camera-panel">
              <div className="panel-heading">
                <div>
                  <div className="eyebrow">Live Camera</div>
                  <h2>{role} at {company}</h2>
                </div>
                <div className="emotion-chip">
                  <span>{currentEmotion}</span>
                  <strong>{Math.round(currentEmotionConfidence * 100)}%</strong>
                </div>
              </div>

              <div className="video-stage">
                <video ref={videoRef} autoPlay playsInline muted className="video" />
                <div className="video-hud">
                  <div className="hud-pill hud-live"><i className="live-dot" />REC</div>
                  <div className="hud-pill">CAM 01</div>
                  <div className="hud-pill">{currentPhase === "dsa" ? "CODING FEED" : "INTERVIEW FEED"}</div>
                </div>
                <div className="camera-overlay">
                  {currentPhase === "dsa" ? "DSA round live" : "AI interview live"}
                </div>
                <div className="camera-scanlines" aria-hidden="true" />
              </div>

              <canvas ref={canvasRef} style={{ display: "none" }} />
            </section>

            <section className={`chat-panel ${currentPhase === "dsa" ? "dsa-mode" : ""}`}>
              <div className="chat-header">
                <div>
                  <div className="eyebrow">AI Interviewer</div>
                  <h1>Voice-first Interview Chat</h1>
                </div>
                <div className="header-actions">
                  <div className="studio-chip">
                    <span>Mode</span>
                    <strong>{currentPhase === "dsa" ? "Studio Coding" : "Studio Q&A"}</strong>
                  </div>
                  <button
                    onClick={() => speak(currentQuestion)}
                    className="button-secondary"
                    disabled={!voiceSupported || !currentQuestion}
                  >
                    Play Question
                  </button>
                  <button onClick={stopInterview} className="button-danger" disabled={loading}>
                    Stop Interview
                  </button>
                </div>
              </div>

              <div className="chat-area" ref={chatAreaRef}>
                {messages.map((message, index) => (
                  <div
                    key={`${message.type}-${index}`}
                    className={
                      message.type === "ai"
                        ? "msg ai"
                        : message.type === "user"
                          ? "msg user"
                          : message.type === "code"
                            ? "msg code"
                          : "msg meta"
                    }
                  >
                    {message.type === "code" ? (
                      <div className="code-msg-wrap">
                        <div className="code-msg-header">
                          <span>Submitted Solution</span>
                          <strong>{message.language || currentLanguage}</strong>
                        </div>
                        <pre className="code-msg-body">
                          <code>{message.text}</code>
                        </pre>
                      </div>
                    ) : (
                      message.text
                    )}
                  </div>
                ))}
              </div>

              <div
                ref={composerRef}
                className={`composer-card ${currentPhase === "dsa" ? "dsa-composer" : ""}`}
              >
                <div className="composer-header">
                  <div>
                    <strong>
                      {currentPhase === "dsa"
                        ? "DSA round: solve in the in-browser IDE"
                        : "Answer with text, speech, or both"}
                    </strong>
                    <p>
                      {currentPhase === "dsa"
                        ? "This stage behaves like a lightweight coding workspace with language selection and evaluator output."
                        : "The AI asks resume-aware questions aloud while you reply in chatbot form."}
                    </p>
                  </div>
                  {currentPhase === "dsa" ? (
                    <select
                      value={currentLanguage}
                      onChange={(event) => setCurrentLanguage(event.target.value)}
                      className="language-select"
                    >
                      {languageOptions.map((option) => (
                        <option key={option.value} value={option.value}>
                          {option.label}
                        </option>
                      ))}
                    </select>
                  ) : null}
                </div>

                {currentPhase === "dsa" ? (
                  <div className="ide-shell">
                    <div className="ide-sidebar">
                      <div className="ide-pane-title">Workspace</div>
                      <div className="ide-file active">solution.{getCurrentLanguageExtension()}</div>
                      <div className="ide-file">prompt.md</div>
                      <div className="ide-file">notes.txt</div>
                    </div>
                    <div className="ide-editor-pane">
                      <div className="ide-toolbar">
                        <span>Live coding editor</span>
                        <strong>{currentLanguage}</strong>
                      </div>
                      <textarea
                        value={codeAnswer}
                        onChange={(event) => setCodeAnswer(event.target.value)}
                        placeholder="Write your DSA solution here..."
                        className="code-editor"
                      />
                    </div>
                  </div>
                ) : (
                  <textarea
                    value={answer}
                    onChange={(event) => setAnswer(event.target.value)}
                    placeholder="Type your answer here, or use voice input..."
                    className="answer-editor"
                  />
                )}

                <div className="tool-row">
                  <button
                    onClick={() => startVoiceInput(true)}
                    className="button-secondary"
                    disabled={listening || !speechSupported || currentPhase === "dsa"}
                  >
                    {listening ? "Listening..." : "Speak Answer"}
                  </button>
                  <button onClick={advanceInterview} className="button-primary" disabled={loading}>
                    {currentPhase === "dsa" ? "Submit and Next" : "Next"}
                  </button>
                </div>

                <div className="voice-note">
                  <p>
                    {speechSupported
                      ? "Speak Answer writes your spoken response into the answer box automatically."
                      : "Speech recognition is unavailable in this browser, so use typed answers here."}
                  </p>
                </div>

                {loading ? <p className="loading-text">Thinking and preparing the next step...</p> : null}
              </div>
            </section>
          </div>

          <div className="interview-status-row">
            <div className="status-group overview-group">
              <div className="status-group-title">Live Overview</div>
              <div className="overview-grid">
                <div className="session-chip neutral">
                  <span>Broadcast</span>
                  <strong className="live-inline"><i className="live-dot" />Live Studio</strong>
                </div>
                <div className="session-chip neutral">
                  <span>Current Round</span>
                  <strong>{currentPhase === "dsa" ? "DSA / Coding" : "Behavioral / Technical"}</strong>
                </div>
                <div className="session-chip neutral">
                  <span>Question Source</span>
                  <strong>
                    {questionSource === "ollama" || questionSource === "ollama-fallback-model"
                      ? questionModel || "Ollama"
                      : "Fallback"}
                  </strong>
                </div>
                <div className="session-chip neutral">
                  <span>Live Emotion</span>
                  <strong>{currentEmotion}</strong>
                </div>
              </div>
            </div>

            <div className="status-group">
              <div className="status-group-title">Live Camera Status</div>
              <div className="camera-stats">
                <div className="stat-tile">
                  <span>Stage</span>
                  <strong>{currentPhase === "dsa" ? "DSA Round" : "Interview Round"}</strong>
                </div>
                <div className="stat-tile">
                  <span>Question</span>
                  <strong>{questionCount || 1}</strong>
                </div>
                <div className="stat-tile">
                  <span>Emotion Status</span>
                  <strong>{emotionStatus}</strong>
                </div>
              </div>
            </div>

            <div className="status-group">
              <div className="status-group-title">Interview Session</div>
              <div className="session-bar">
                <div className={`session-chip ${questionSource === "ollama" || questionSource === "ollama-fallback-model" ? "healthy" : "warning"}`}>
                  <span>Question Source</span>
                  <strong>
                    {questionSource === "ollama" || questionSource === "ollama-fallback-model"
                      ? questionModel || "Ollama"
                      : liveHealth.ollama
                        ? "Fallback for this question"
                        : "Fallback"}
                  </strong>
                </div>
                <div className="session-chip neutral">
                  <span>Input Mode</span>
                  <strong>{currentPhase === "dsa" ? "IDE + Evaluation" : "Voice + Text Chat"}</strong>
                </div>
                <div className="session-chip neutral">
                  <span>Round</span>
                  <strong>{currentPhase === "dsa" ? "Coding / DSA" : "Behavioral / Technical"}</strong>
                </div>
              </div>
            </div>

            <div className="status-group">
              <div className="status-group-title">System Health</div>
              <div className="camera-health-stack">
                <div className={`health-item ${liveHealth.backend ? "healthy" : "offline"}`}>
                  <span>Backend</span>
                  <strong>{liveHealth.backend ? "Online" : "Offline"}</strong>
                </div>
                <div className={`health-item ${liveHealth.ollama ? "healthy" : "warning"}`}>
                  <span>Model Service</span>
                  <strong>{liveHealth.ollama ? "Ollama live" : "Model unavailable"}</strong>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Interview;
