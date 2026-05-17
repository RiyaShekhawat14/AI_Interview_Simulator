# AI Interview App: Architecture, End-to-End Flow, File Guide, and FAANG Interview Prep

## 1. Executive Summary

This project is a full-stack AI mock interview platform with five major capabilities:

1. Resume-aware interview question generation
2. Voice, text, and camera-based interview interaction
3. A DSA coding round with code evaluation
4. A final coaching report with corrected answers and corrected DSA solutions
5. Account-based authentication with persisted user-scoped sessions and reports

The stack is:

- Frontend: React + Vite
- Backend: FastAPI
- Persistence: SQLAlchemy with SQLite locally and Postgres-ready deployment support
- Local LLM: Ollama
- Emotion model: PyTorch + OpenCV
- Speech-to-text: Whisper

At runtime, the app behaves like this:

1. The user opens the React frontend.
2. The setup page checks backend and Ollama health.
3. The user signs in or creates an account.
4. The user uploads a resume PDF.
5. The backend extracts resume text.
6. The interview page starts a backend session.
7. The backend asks 5 general questions and then 2 DSA questions.
8. During the interview, the frontend captures webcam frames and sends them to the backend for emotion detection.
9. The frontend can read questions aloud and capture spoken answers into the answer box.
10. DSA answers are evaluated by Ollama or a local fallback evaluator.
11. At the end, the backend generates a detailed report with scores, strengths, weaknesses, corrected answers, and corrected code.

This is not just a chatbot. It is a multi-modal interview simulator with orchestration across browser APIs, FastAPI endpoints, local AI models, and classical fallback logic.

## 2. High-Level Architecture

### 2.1 Main Layers

The app has four logical layers:

1. Presentation layer
- React pages render the user interface.
- Browser APIs provide camera, speech recognition, and speech synthesis.

2. API layer
- FastAPI exposes endpoints for interview session control, resume upload, code evaluation, speech-to-text, emotion detection, and reporting.

3. Service layer
- Python service modules handle question generation, report generation, code evaluation, emotion inference, and speech transcription.

4. Model / inference layer
- Ollama provides LLM-backed question generation, code review, and report enhancement.
- A PyTorch emotion classifier predicts emotional state from webcam frames.
- Whisper transcribes user speech.

### 2.2 Architecture Diagram in Words

Frontend -> FastAPI routes -> services -> local models / fallback logic

More concretely:

- `Setup.jsx` calls `/health` and `/upload-resume`
- `Interview.jsx` calls `/interview/start`, `/interview/next`, `/interview/submit-code`, `/detect-emotion`, `/interview/report`
- `Report.jsx` renders the aggregated interview report
- `question_service.py` talks to Ollama for question generation
- `code_service.py` talks to Ollama for DSA evaluation
- `report_service.py` talks to Ollama for corrected answers and coaching feedback
- `emotion_model.py` runs a local ResNet18-based classifier
- `speech_service.py` runs Whisper transcription

## 3. End-to-End User Flow

## 3.1 Home Page Flow

File: `frontend/src/pages/Home.jsx`

What happens:

1. The page loads.
2. It calls `checkHealth()` from `frontend/src/services/api.js`.
3. The backend responds from `/health`.
4. The page shows whether backend and Ollama are available.
5. The user chooses either:
- `Launch Interview`
- `Open Last Report`

Purpose:
- Acts as the landing page and runtime health dashboard.

## 3.2 Setup Page Flow

File: `frontend/src/pages/Setup.jsx`

What happens:

1. The page again checks health via `/health`.
2. The user enters:
- company
- role
- resume PDF
3. The file is posted to `/upload-resume`.
4. The backend extracts raw text from the PDF.
5. The frontend stores extracted resume text in `localStorage`.
6. The frontend navigates to `/interview` and passes:
- role
- company
- resume text

Purpose:
- Collects the interview context that makes questions more personalized.

## 3.3 Interview Page Flow

File: `frontend/src/pages/Interview.jsx`

This is the core orchestration page.

What happens on mount:

1. Validate that role and company exist; otherwise redirect to setup.
2. Refresh backend health.
3. Start webcam stream with `getUserMedia`.
4. Start the interview session by posting to `/interview/start`.
5. Request the first question from `/interview/next`.
6. Save the active question and phase in state.
7. Speak the question aloud with browser speech synthesis.
8. If browser speech recognition is supported, start listening after TTS finishes.

Behavioral round:

1. User types or speaks an answer.
2. Spoken text is appended directly into the answer textbox.
3. Before moving to the next question, the page captures the latest emotion snapshot.
4. The answer and emotion are sent to `/interview/next`.
5. The backend stores the response and returns the next question.

DSA round:

1. After 5 general questions, the backend changes the phase to `dsa`.
2. The UI switches from text answer mode to the IDE-like code editor.
3. The user submits code via `/interview/submit-code`.
4. The backend evaluates the code.
5. The frontend immediately requests the next question or final report.

Finish flow:

1. When the backend returns `phase = complete`, the frontend calls `/interview/report`.
2. The report is saved in `localStorage`.
3. The app navigates to `/report`.

## 3.4 Report Page Flow

File: `frontend/src/pages/Report.jsx`

What happens:

1. The page reads report data from route state or `localStorage`.
2. It renders:
- overall score
- assessment
- confidence summary
- communication summary
- strengths
- weaknesses
- recommendations
- per-question review
3. For DSA entries, it also renders corrected solution code.
4. The user can download the report JSON.

Purpose:
- Turns raw responses into interview coaching.

## 4. Backend Request Flow

## 4.1 Application Bootstrap

File: `backend/main.py`

Responsibilities:

- Creates the FastAPI app
- Configures CORS
- Registers route modules

Routers included:

- `question_router`
- `interview_router`
- `report_router`
- `upload_router`
- `code_router`
- `health_router`

This is the root composition file for the backend.

## 4.2 Health Check

File: `backend/routes/health.py`

Endpoint:

- `GET /health`

Responsibilities:

- Returns backend status
- Tries a lightweight Ollama call through `check_ollama()`
- Returns model name, URL, and latency if successful

Why it matters:
- The frontend uses it to determine whether live LLM responses or fallback mode will be active.

## 4.3 Resume Upload

File: `backend/routes/upload.py`

Endpoint:

- `POST /upload-resume`

Responsibilities:

- Accepts a PDF file
- Extracts text with `pypdf` or `PyPDF2`
- Returns extracted text to the authenticated frontend flow and keeps the shared resume helper for the standalone question endpoint
- Returns extracted text and length

Key design choice:
- The main interview flow passes resume text into a user-scoped persisted session record, while the shared resume helper remains as a lightweight compatibility path for the standalone question endpoint.

## 4.4 Interview Session Engine

File: `backend/routes/interview.py`

This is the most important backend file.

Key endpoints:

- `POST /interview/start`
- `POST /interview/next`
- `POST /interview/submit-code`
- `POST /interview/report`
- `POST /speech-to-text`
- `POST /detect-emotion`

Core session object:

The app keeps each live interview in a hot in-process cache and also persists the session in the database. Each session tracks:

- role
- company
- resume text
- phase
- question count
- DSA count
- responses
- asked questions
- emotion history
- preferred language
- current question
- start time

Why this works:
- Fast local request handling
- Session recovery after backend restarts
- User-scoped isolation for multi-user usage

Tradeoff:
- The current setup is suitable for a single backend instance or small launch
- Higher-scale production would still benefit from Redis or another dedicated distributed cache

### `/interview/start`

Creates a new session and returns a session ID.

### `/interview/next`

Responsibilities:

- Save the previous behavioral answer
- Attach client-captured emotion metadata
- Decide whether the app is still in `general`, has moved to `dsa`, or is `complete`
- Call `generate_question_result(...)`
- Avoid repeated questions by tracking `asked_questions`

Phase rules:

- First 5 questions: general
- Next 2 questions: dsa
- After that: complete

### `/interview/submit-code`

Responsibilities:

- Validate that the session is in DSA phase
- Evaluate the submitted code using `services.code_service.evaluate_code`
- Store the code answer and evaluation in the session

### `/interview/report`

Responsibilities:

- Generate the final aggregated report using `generate_interview_report`
- Delete the session from memory afterward

### `/speech-to-text`

Responsibilities:

- Save uploaded audio temporarily
- Use `speech_service.transcribe_audio(...)`
- Return transcription text
- Gracefully handle missing Whisper availability

### `/detect-emotion`

Responsibilities:

- Read uploaded image bytes
- Call `detect_emotion_bytes(...)`
- Normalize and return emotion, confidence, status, and reliability

## 5. Core Service Layer

## 5.1 Question Generation Service

File: `backend/services/question_service.py`

Responsibilities:

- Encapsulates all Ollama question-generation logic
- Supports a primary model and a fallback model
- Supports full fallback to hard-coded questions
- Cleans and normalizes generated questions

Key functions:

- `_call_llama(...)`
- `check_ollama()`
- `generate_question_result(...)`
- `generate_question(...)`

Question sources:

1. Primary Ollama model
2. Secondary Ollama model
3. Hard-coded fallback pool

This is a strong resilience pattern. The app degrades gracefully instead of breaking.

## 5.2 Code Evaluation Service

File: `backend/services/code_service.py`

Responsibilities:

- Sends DSA code and prompt context to Ollama for evaluation
- Falls back to a rule-based evaluator if the LLM is unavailable

Evaluation output includes:

- verdict
- score
- issues
- suggestions

Why this matters:
- The app can still complete the DSA flow even without a live LLM.

## 5.3 Report Generation Service

File: `backend/services/report_service.py`

This is the richest intelligence layer in the app.

Responsibilities:

- Score each response
- Detect filler-word pressure
- Summarize emotion patterns
- Generate corrected answers
- Generate corrected DSA code
- Build the final coaching report

Important helper logic:

- `_score_response(...)`
- `_emotion_summary(...)`
- `_confidence_band(...)`
- `_communication_band(...)`
- `_generate_ai_review(...)`
- `_fallback_corrected_answer(...)`
- `_fallback_corrected_code(...)`

Output fields include:

- overall score
- assessment
- emotion summary
- confidence report
- communication report
- strengths
- weaknesses
- recommendations
- enriched per-response feedback

This file is effectively the coaching brain of the app.

## 5.4 Emotion Service

File: `backend/services/emotion_service.py`

Responsibilities:

- Thin wrapper around the emotion model
- Keeps route logic separate from model logic

Functions:

- `detect_emotion(image_path)`
- `detect_emotion_bytes(image_bytes)`

## 5.5 Speech Service

File: `backend/services/speech_service.py`

Responsibilities:

- Load Whisper
- Confirm model availability
- Transcribe audio files
- Decode WAV audio directly in Python
- Resample audio to 16 kHz when needed

Key functions:

- `load_model()`
- `speech_model_available()`
- `transcribe_audio(...)`

Good design detail:
- WAV audio can be handled without relying on external `ffmpeg` for the simple path.

## 6. Emotion Model Flow

File: `backend/models/emotion_model.py`

This file implements local emotion classification.

Pipeline:

1. Load a ResNet18 backbone
2. Replace the classification head with 3 classes
3. Load `best_model.pth` if available
4. Detect the face using OpenCV Haar cascade
5. Crop the most prominent face
6. Create multiple image variants:
- resized
- CLAHE-enhanced
- horizontally flipped
7. Run inference on each variant
8. Average the logits
9. Apply temperature-adjusted softmax
10. Smooth predictions using a short history deque
11. Map raw labels to UI-friendly labels:
- `interested` -> `Confident`
- `neutral` -> `Normal`
- `Disappointed` -> `Nervous`
12. If confidence is too low, default to `Normal`

Why this is a smart design:

- Ensemble-style inference improves stability
- Prediction smoothing avoids noisy UI jitter
- Low-confidence fallback prevents overclaiming emotion certainty

## 7. Frontend Architecture

## 7.1 Router Layer

Files:

- `frontend/src/main.jsx`
- `frontend/src/App.jsx`

Responsibilities:

- Boot React
- Register the client router
- Map routes to pages

Routes:

- `/` -> `Home`
- `/setup` -> `Setup`
- `/interview` -> `Interview`
- `/report` -> `Report`

## 7.2 API Client Layer

File: `frontend/src/services/api.js`

Responsibilities:

- Centralize frontend-to-backend HTTP calls
- Keep pages cleaner by hiding request details

Main API functions:

- `checkBackend`
- `checkHealth`
- `uploadResume`
- `startInterviewSession`
- `getNextInterviewQuestion`
- `submitCodeAnswer`
- `getInterviewReport`
- `speechToText`
- `detectEmotion`
- `evaluateCode`
- `getFinalReport`

This is the single API gateway from React into FastAPI.

## 7.3 Styling Layer

Files:

- `frontend/src/App.css`
- `frontend/src/index.css`

Responsibilities:

- Global UI theme
- Home, setup, interview, and report page layouts
- IDE styling
- dark report page styling
- mobile responsiveness

`App.css` currently contains most of the visual system.

## 8. File-by-File Guide

This section separates active files from supporting or legacy files.

## 8.1 Root Files

- `README.md`
  - Project overview and current run instructions.
- `render.yaml`
  - Render deployment config for the backend.
- `split_dataset.py`
  - Dataset-preparation helper, not used during app runtime.
- `TEST_WALKTHROUGH.md`
  - Manual testing notes / walkthrough.
- `dummy_resume.pdf`
  - Sample PDF for testing uploads.
- `.gitignore`
  - Ignore rules for local artifacts, builds, and runtime files.

## 8.2 Backend Core Runtime Files

- `backend/main.py`
  - FastAPI bootstrapper and router registration.
- `backend/run_backend.ps1`
  - Local backend launcher with environment defaults and `.venv` preference.
- `backend/requirements.txt`
  - Backend Python dependencies.

## 8.3 Backend Routes

- `backend/routes/health.py`
  - Backend + Ollama health probe.
- `backend/routes/upload.py`
  - Resume PDF upload and text extraction.
- `backend/routes/question.py`
  - Standalone question endpoint using the shared resume store.
- `backend/routes/code.py`
  - Standalone code-evaluation endpoint.
- `backend/routes/report.py`
  - Standalone final report endpoint.
- `backend/routes/interview.py`
  - Main interview session controller and multi-modal endpoints.
- `backend/routes/__init__.py`
  - Package marker.

## 8.4 Backend Services Used in the Main Flow

- `backend/services/question_service.py`
  - LLM + fallback question generation.
- `backend/services/code_service.py`
  - LLM + fallback DSA evaluation.
- `backend/services/report_service.py`
  - Final scoring, corrected answers, corrected code, feedback.
- `backend/services/emotion_service.py`
  - Emotion inference wrapper.
- `backend/services/speech_service.py`
  - Whisper speech transcription.
- `backend/services/resume_store.py`
  - In-memory shared resume text holder.

## 8.5 Backend Services Present but Not Central to Current Runtime

- `backend/services/confidence_service.py`
  - Simple word-count confidence heuristic; current report flow uses richer logic elsewhere.
- `backend/services/evaluation_service.py`
  - Embedding or similarity-based answer evaluator; not currently wired into the main interview route.
- `backend/services/nlp_services.py`
  - Alternate answer-evaluation helper with sentence-transformers; not currently used in the main flow.
- `backend/services/rag_service.py`
  - Minimal placeholder RAG helper.
- `backend/services/resume_service.py`
  - File-path-based resume extractor, while the active upload route uses in-memory bytes.
- `backend/services/__init__.py`
  - Package marker.

## 8.6 Backend Models

- `backend/models/emotion_model.py`
  - Core local emotion model and inference pipeline.
- `backend/models/best_model.pth`
  - Trained weights used by the emotion model.
- `backend/models/npl_model.py`
  - Sentence-transformer helper; not part of the main runtime path.

## 8.7 Backend Utility / Training Files

- `backend/train_emotion_model.py`
  - Model training script, not used in live app flow.
- `backend/utlis/audio_processing.py`
  - Utility helper area; not part of the currently active path.
- `backend/utlis/video_processing.py`
  - Utility helper area; not part of the currently active path.
- `backend/utlis/resume_parser.py`
  - Utility helper area; not part of the currently active path.
- `backend/utlis/__init__.py`
  - Package marker.

Note:
- The folder name is `utlis`, not `utils`. That looks like a typo-based legacy folder name.

## 8.8 Frontend Core Runtime Files

- `frontend/index.html`
  - Root HTML shell for the Vite app.
- `frontend/package.json`
  - Frontend scripts and dependencies.
- `frontend/package-lock.json`
  - Locked package versions.
- `frontend/vite.config.js`
  - Vite config.
- `frontend/vercel.json`
  - SPA rewrite configuration for Vercel.
- `frontend/src/main.jsx`
  - React bootstrap entry.
- `frontend/src/App.jsx`
  - Route map.
- `frontend/src/App.css`
  - Main application styling.
- `frontend/src/index.css`
  - Base styling entry.
- `frontend/src/services/api.js`
  - HTTP client layer.

## 8.9 Frontend Active Pages

- `frontend/src/pages/Home.jsx`
  - Landing page + health dashboard.
- `frontend/src/pages/Setup.jsx`
  - Resume / role / company setup flow.
- `frontend/src/pages/Interview.jsx`
  - Main live interview experience.
- `frontend/src/pages/Report.jsx`
  - Final coaching report experience.

## 8.10 Frontend Components Likely Legacy or No Longer Wired

These files exist, but the current app primarily uses page-level implementations instead of composing these components:

- `frontend/src/components/AudioRecorder.jsx`
  - Standalone voice-detection recorder component; not currently mounted in the active pages.
- `frontend/src/components/WebcamCapture.jsx`
  - Standalone webcam emotion component; logic is now mostly embedded directly in `Interview.jsx`.
- `frontend/src/components/AnswerBox.jsx`
  - Small answer textarea component; not currently used.
- `frontend/src/components/QuestionBox.jsx`
  - Small question display component; not currently used.
- `frontend/src/components/ResumeUpload.jsx`
  - Isolated upload component; setup page currently handles upload inline.
- `frontend/src/components/RoleInput.jsx`
  - Small role input component; not currently used.
- `frontend/src/components/CompanyDropdown.jsx`
  - Company selector helper; not currently used.
- `frontend/src/components/Navbar.jsx`
  - Navigation helper; not currently used.
- `frontend/src/components/ResultCard.jsx`
  - Simple result renderer; not currently used.

This is a useful talking point in interviews: the codebase shows evidence of evolution from a component-demo style into a more page-driven product flow.

## 9. Data Flow by Feature

## 9.1 Resume-Aware Questioning

Flow:

1. User uploads PDF.
2. Backend extracts resume text.
3. Resume text is stored locally and passed into interview session creation.
4. `question_service.py` uses resume hints in the prompt.
5. Questions become more contextual than generic interview prompts.

## 9.2 Emotion Tracking

Flow:

1. Browser camera starts.
2. Frontend captures frame snapshots on an interval.
3. Image bytes are sent to `/detect-emotion`.
4. Backend classifies emotion with `emotion_model.py`.
5. Frontend stores current emotion and confidence.
6. That emotion metadata is attached to answer submissions and later appears in the report.

## 9.3 Voice Support

Text-to-speech flow:

1. Frontend receives next question.
2. Browser `SpeechSynthesisUtterance` reads the question aloud.

Speech-to-text flow:

1. Browser speech recognition captures spoken text.
2. Final recognized text is appended into the chat answer box.
3. Separate backend speech-to-text also exists for uploaded audio processing.

## 9.4 DSA Evaluation

Flow:

1. Backend switches phase after 5 general questions.
2. Frontend renders code editor.
3. Code is posted to `/interview/submit-code`.
4. `code_service.py` sends prompt + code to Ollama.
5. If Ollama fails, fallback evaluator produces a heuristic verdict.
6. Report layer later uses that evaluation plus corrected code generation.

## 10. Strengths of the Architecture

1. Graceful degradation
- The app keeps working if Ollama is down by using fallback questions and fallback code/report logic.

2. Clear separation of concerns
- Routes orchestrate HTTP.
- Services contain business logic.
- Models handle inference.
- React pages handle UX.

3. Good demo-to-product progression
- The app combines multiple signals: resume, emotion, speech, and code.

4. Strong interview-story value
- This is a strong project for discussing full-stack orchestration, AI integration, and fault tolerance.

5. Local-first AI workflow
- The app does not depend entirely on a cloud API.

## 11. Current Design Limitations

These are important to mention honestly in interviews.

1. Single-instance session strategy
- Sessions are now persisted in the database, but the current hot-cache approach is still designed for a single backend instance rather than a distributed fleet.

2. Partial legacy resume helper
- `resume_store.resume_text` still exists for the standalone question endpoint, even though the main interview flow now uses persisted user-scoped session state.

3. Browser API variability
- Speech recognition behavior varies across browsers.

4. Basic auth lifecycle only
- The app now uses JWT-based user authentication, but it does not yet include refresh tokens, password reset flows, email verification, or RBAC.

5. Early-stage persistence model
- Users, sessions, and reports are now stored in a database, but there is no migration system or dedicated cache layer yet.

6. Sync model calls
- Routes are standard FastAPI handlers but most heavy inference work is synchronous and blocking.

7. Legacy file drift
- There are unused helper components and services that could be cleaned up.

## 12. How to Explain This Project in an Interview

Use this short answer:

"I built a full-stack AI mock interview simulator using React and FastAPI. The frontend collects role, company, resume, camera, and speech input, while the backend orchestrates interview sessions, Ollama-based question generation, Whisper speech transcription, a PyTorch emotion model, DSA code evaluation, and a coaching-style final report. One of the design goals was graceful degradation, so if the local LLM is unavailable, the app still works with fallback questions and local evaluation logic."

## 13. FAANG-Style Interview Questions and Strong Answers

## Q1. Walk me through the architecture of this project.

Strong answer:

"The app has a React frontend and a FastAPI backend. The frontend handles user interaction across four pages: home, setup, interview, and report. The backend exposes endpoints for resume upload, session control, emotion detection, speech transcription, code evaluation, and reporting. The business logic lives in service modules like `question_service.py`, `code_service.py`, and `report_service.py`. Ollama handles LLM-powered generation and evaluation, Whisper handles speech-to-text, and a local PyTorch model handles emotion detection. The overall request flow is frontend page -> API client -> FastAPI route -> service -> model or fallback logic."

## Q2. Why did you separate route files from service files?

Strong answer:

"I separated them to keep HTTP concerns and business logic independent. Route files parse request data, validate basic flow, and shape responses. Service files contain reusable logic like calling Ollama, scoring answers, or generating reports. That makes the system easier to test, evolve, and reason about. If I later changed the transport layer, most of the service logic could remain unchanged."

## Q3. How does the interview session state work?

Strong answer:

"Each live interview session is stored in an in-memory dictionary keyed by session ID. A session tracks the role, company, resume text, phase, asked questions, user responses, emotion history, and timing. This made iteration very fast for a local-first product. The tradeoff is that the state is not persistent and would not scale across multiple backend workers, so in a production rewrite I’d move this to Redis or a database-backed session store."

## Q4. How do you prevent the app from failing when Ollama is unavailable?

Strong answer:

"The design uses layered fallback logic. For question generation, the app first tries the primary Ollama model, then a configured fallback model, and finally a hard-coded fallback question pool. Code evaluation also has a fallback evaluator, and report generation has fallback corrected answers and code snippets. That means the user still gets a complete interview flow even when local inference is unavailable or too slow."

## Q5. How is resume context used?

Strong answer:

"After PDF upload, the backend extracts text and passes a trimmed resume excerpt into the question-generation prompt. That gives the interviewer more context about the candidate’s background, which makes the questions feel more personalized. The service only uses a limited excerpt to keep prompts smaller and more stable."

## Q6. How does the emotion detection pipeline work?

Strong answer:

"The browser periodically captures webcam frames and sends them to the backend. The backend detects the face with OpenCV, creates multiple image variants, runs a ResNet18-based classifier, averages logits, applies temperature-adjusted softmax, and smooths predictions over recent frames. If confidence is too low, it defaults to a neutral state rather than overclaiming emotional certainty."

## Q7. Why did you choose to default low-confidence emotion predictions to normal?

Strong answer:

"Emotion inference is noisy, and a false confident label is worse than a conservative neutral label in this product. The app uses confidence, entropy, and class margin checks, and if the signal is weak it falls back to `Normal`. That gives more stable UX and prevents misleading feedback in the final report."

## Q8. How does speech input work in the app?

Strong answer:

"For the live behavioral flow, the browser uses speech recognition and appends final transcripts directly into the answer box. For backend transcription capability, the app also exposes a `/speech-to-text` endpoint that can accept uploaded audio and transcribe it with Whisper. So there’s both a lightweight browser path and a model-backed server path."

## Q9. How does the DSA round differ from the general interview round?

Strong answer:

"The interview is phase-based. The backend starts in a general question phase and counts responses. After five general questions, it switches the session to a DSA phase. The frontend reacts to that by replacing the answer box with an IDE-style code editor and language selector. Code submissions go through a different endpoint and evaluation path than behavioral answers."

## Q10. How are answers scored in the final report?

Strong answer:

"The report service uses heuristic scoring rather than a single black-box score. For behavioral answers it looks at answer depth, filler words, and emotion signals. For DSA answers it also considers code length and evaluation feedback. Then it enriches each response with an AI-generated corrected answer, improvement note, and for DSA items a corrected code solution."

## Q11. What production issues would you fix first?

Strong answer:

"The first production changes would be replacing in-memory session state with Redis or a database, isolating resume storage per user, adding authentication, adding structured logging and rate limiting, and moving long-running inference tasks off the request thread where needed. I’d also clean up legacy components and unused helper files to reduce maintenance overhead."

## Q12. Why is this project a good systems design discussion piece?

Strong answer:

"Because it combines frontend state orchestration, backend session management, local AI inference, fallback resilience, browser APIs, and report generation in one flow. It gives room to discuss architecture, tradeoffs, reliability, UX, and scaling rather than just one algorithm."

## Q13. If you had to scale this to thousands of users, what would you redesign?

Strong answer:

"I’d externalize session state and reports into a database, store uploaded resumes in object storage, use a job queue for heavy report generation or transcription, serve model inference behind separate worker services, and cache static fallback assets aggressively. I’d also introduce authentication, metrics, and autoscaling policies around the inference services."

## Q14. What are the most interesting technical decisions in this codebase?

Strong answer:

"The most interesting ones are the graceful degradation strategy for LLM unavailability, the phase-based interview engine, the multi-signal final report that combines content and emotion, and the emotion model’s smoothing and confidence gating. Those choices make the app feel more robust than a simple prompt-wrapper demo."

## Q15. What would a FAANG interviewer challenge you on in this project?

Strong answer:

"They would likely challenge the use of in-memory state, absence of persistent storage, possible browser compatibility issues for speech APIs, and whether the heuristic scoring is rigorous enough. The best response is to be honest that the current version is optimized for a local working product, then explain the exact production upgrades I’d make next."

## 14. Quick Revision Sheet

If you need a fast prep answer, remember these seven points:

1. React frontend, FastAPI backend
2. Resume upload personalizes prompts
3. Ollama generates questions, evaluates code, and helps build reports
4. Whisper handles speech-to-text
5. PyTorch + OpenCV handle emotion detection
6. Session engine controls general -> DSA -> report flow
7. Fallback logic keeps the app usable even without live LLM responses

## 15. Suggested Short Pitch for the Project

"This is a full-stack AI interview simulator that combines resume-aware LLM prompting, browser voice UX, local emotion detection, DSA code evaluation, and a coaching-style report. The core engineering challenge was orchestration and resilience: multiple AI and browser subsystems need to work together, and the product still needs to function when one subsystem fails."
