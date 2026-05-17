## AI Interview Project

Full-stack AI interview simulator with:

- React + Vite frontend
- FastAPI backend
- Resume upload and parsing
- Camera-based emotion detection
- Text-to-speech question playback
- Speech-to-text answer capture
- General interview round plus DSA coding round
- Final coaching report

## Launch Readiness

The app now includes:

- frontend lint-clean production build
- JWT-based user authentication
- database-backed persistence for users, interview sessions, and saved reports
- session TTL cleanup for abandoned interview sessions
- fallback behavior when Ollama is unavailable
- request metrics middleware with a `/metrics` endpoint
- TTL cache support for health probes, question generation, code evaluation, and report reads
- optional Redis-backed cache mode through `REDIS_URL`
- request logging and rate limiting middleware
- a protected frontend operations dashboard at `/ops`

Current production caveats:

- Local development defaults to SQLite; for real launches, use a managed Postgres `DATABASE_URL`.
- Session state is now persisted in the database, but very high-scale traffic would still benefit from a dedicated cache or worker model.
- The built-in cache is an in-memory TTL cache suited to single-instance deployments; multi-instance production scaling would still move this to Redis or a similar shared cache.
- Whisper, Ollama, and the emotion model still depend on the deployed runtime having the right Python/system setup.

## Local URLs

- Frontend: `http://127.0.0.1:5175`
- Backend: `http://127.0.0.1:8000`
- Ollama: `http://127.0.0.1:11434`

## Run Locally

Backend:

```powershell
cd backend
.\run_backend.ps1
```

Frontend:

```powershell
cd frontend
npm run dev -- --host 127.0.0.1 --port 5175
```

## Environment

Backend defaults are configured for the models currently installed on this machine:

- `LLAMA_MODEL=mistral:latest`
- `LLAMA_FALLBACK_MODEL=llama3:8b`
- `LLAMA_TIMEOUT_SECONDS=45`
- `SESSION_TTL_SECONDS=7200`
- `DATABASE_URL=sqlite:///C:/path/to/ai_interview_app.db`
- `JWT_SECRET=...`
- `JWT_EXPIRES_MINUTES=720`
- `CACHE_ENABLED=true`
- `REDIS_URL=redis://...`
- `REDIS_NAMESPACE=ai_interview`
- `HEALTH_CACHE_TTL_SECONDS=15`
- `QUESTION_CACHE_TTL_SECONDS=180`
- `CODE_CACHE_TTL_SECONDS=300`
- `REPORT_CACHE_TTL_SECONDS=30`
- `RATE_LIMIT_ENABLED=true`
- `RATE_LIMIT_WINDOW_SECONDS=60`
- `RATE_LIMIT_MAX_REQUESTS=120`

Frontend environment:

- `VITE_API_BASE_URL=http://127.0.0.1:8000`

If Ollama is unavailable or too slow, the app falls back to built-in questions and local scoring logic instead of crashing.

## Deployment Notes

- Backend health now reports `auth_enabled` and `persistence` so you can verify launch configuration quickly.
- `GET /metrics` now exposes request counts, per-route timings, and cache statistics.
- The frontend includes a protected `/ops` route that visualizes request metrics, cache mode, and rate-limit settings.
- Completed interview reports are persisted and available through `GET /reports/history`.
- Authentication uses bearer tokens from `/auth/register` and `/auth/login`.
- `render.yaml` now includes a Render Postgres database binding for the backend service.

See [docs/LAUNCH_CHECKLIST.md](/c:/Users/hp/OneDrive/Desktop/AI_interview_project/docs/LAUNCH_CHECKLIST.md) for a concrete pre-launch checklist.

## Verified Flow

The following flow was tested successfully:

1. Open frontend
2. Upload resume PDF
3. Start interview session
4. Answer 5 general questions
5. Enter 2 DSA answers
6. Generate final report

Also verified:

- Emotion detection endpoint
- Speech-to-text endpoint
- Frontend production build
- Backend health route
- Frontend lint
- Backend import and database initialization

## Browser Notes

For the best live experience, use Chrome or Edge because browser speech recognition support is stronger there.

The following require browser permission prompts and should be manually allowed:

- Camera
- Microphone
- Speech playback
