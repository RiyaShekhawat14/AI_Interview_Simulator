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
- a repeatable backend smoke test via `npm run backend:smoke`
- shared Ollama fallback logic with fast connection-failure cooldowns for smoother deployments without local models
- production-oriented Docker images for both frontend and backend
- sanitized env templates for local setup and deployment handoff

Current production caveats:

- Local development defaults to SQLite; for real launches, use a managed Postgres `DATABASE_URL`.
- Session state is now persisted in the database, but very high-scale traffic would still benefit from a dedicated cache or worker model.
- The built-in cache is an in-memory TTL cache suited to single-instance deployments; multi-instance production scaling would still move this to Redis or a similar shared cache.
- Whisper, Ollama, and the emotion model still depend on the deployed runtime having the right Python/system setup.
- `backend/models/best_model.pth` remains committed intentionally because the emotion detector expects a bundled checkpoint.

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
- `QUESTION_GENERATION_TIMEOUT_SECONDS=6`
- `DSA_GENERATION_TIMEOUT_SECONDS=8`
- `LLAMA_CONNECT_TIMEOUT_SECONDS=1.5`
- `LLAMA_DISABLE_COOLDOWN_SECONDS=30`
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

Example env templates:

- `.env.example`
- `backend/.env.example`
- `frontend/.env.example`

If Ollama is unavailable or too slow, the app falls back to built-in questions and local scoring logic instead of crashing.

## Deployment Notes

- Backend health now reports `auth_enabled` and `persistence` so you can verify launch configuration quickly.
- `GET /metrics` now exposes request counts, per-route timings, and cache statistics.
- The frontend includes a protected `/ops` route that visualizes request metrics, cache mode, and rate-limit settings.
- Completed interview reports are persisted and available through `GET /reports/history`.
- Authentication uses bearer tokens from `/auth/register` and `/auth/login`.
- `render.yaml` now includes a Render Postgres database binding for the backend service.
- When Ollama is unreachable, the backend now fails fast on connection attempts and temporarily cools down instead of repeatedly waiting through long timeouts.

## Docker

You can run the full stack with Docker Compose:

```powershell
copy .env.example .env
docker compose up --build
```

This starts:

- `frontend` on `http://localhost:4173`
- `backend` on `http://localhost:8000`
- `ollama` on `http://localhost:11434`

The backend is wired to Ollama through `http://ollama:11434/api/generate` inside the Compose network, so it works consistently across machines without editing code.

To pre-download the configured Ollama models into the shared Docker volume:

```powershell
docker compose --profile model-setup run --rm ollama-init
```

Notes:

- The first model pull can take a while because `mistral:latest` and `llama3:8b` are large.
- If you do not preload models, the app still runs and falls back gracefully when Ollama is unavailable.
- For production containers, set real values for `JWT_SECRET`, `ALLOWED_ORIGINS`, and `DATABASE_URL` instead of using the development defaults in `docker-compose.yml`.
- The frontend container now builds static assets and serves them through Nginx instead of running the Vite dev server.
- The backend container now runs on `python:3.11-slim`, includes `ffmpeg`, and starts with proxy header support.

## CI

The repo now includes GitHub Actions CI at `.github/workflows/ci.yml` that:

- lints and builds the frontend
- installs backend dependencies and runs the backend smoke test
- builds the backend and frontend Docker images

CI intentionally does not download Ollama models on every run. That keeps pipelines practical while the application still validates its fallback behavior.

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
- Backend smoke test (`npm run backend:smoke`)

## Browser Notes

For the best live experience, use Chrome or Edge because browser speech recognition support is stronger there.

The following require browser permission prompts and should be manually allowed:

- Camera
- Microphone
- Speech playback
