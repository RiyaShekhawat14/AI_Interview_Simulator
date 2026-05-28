# AI Interview Simulator

AI Interview Simulator is a full-stack mock interview platform built to simulate a realistic technical interview flow. It combines resume-aware question generation, voice and text answers, a coding round, emotion detection hooks, and a final report so users can practice in a more structured, product-style environment.

## Live Demo

- Frontend: [ai-interview-simulator-a26hoswav-riyashekhawat14s-projects.vercel.app](https://ai-interview-simulator-a26hoswav-riyashekhawat14s-projects.vercel.app)
- Backend: [ai-interview-simulator-iu72.onrender.com](https://ai-interview-simulator-iu72.onrender.com)
- Backend health: [ai-interview-simulator-iu72.onrender.com/health](https://ai-interview-simulator-iu72.onrender.com/health)

## Features

- JWT-based authentication for user accounts
- Resume upload and parsing
- General interview round with role and company context
- DSA coding round with code submission flow
- Speech-to-text answer capture
- Text-to-speech prompt playback
- Emotion detection integration path
- Saved reports and interview history
- Metrics, health checks, rate limiting, and cache support
- Fallback behavior when Ollama is unavailable

## Screenshots

Add your screenshots here after upload.

```md
![Home Screen](./docs/screenshots/home.png)
![Interview Setup](./docs/screenshots/setup.png)
![Interview Flow](./docs/screenshots/interview.png)
![Final Report](./docs/screenshots/report.png)
```

## Tech Stack

- Frontend: React, Vite, Axios, React Router
- Backend: FastAPI, SQLAlchemy, Uvicorn
- Database: PostgreSQL
- AI/ML integrations: Ollama, Whisper, emotion model hooks
- Deployment: Vercel frontend, Render backend

## Project Structure

```text
AI_interview_project/
├── backend/
├── frontend/
├── docs/
├── database/
├── dataset/
├── docker-compose.yml
└── render.yaml
```

## Local Development

### 1. Clone and install

```powershell
git clone <your-repo-url>
cd AI_interview_project
```

### 2. Backend

```powershell
cd backend
.\run_backend.ps1
```

Backend runs at:

```text
http://127.0.0.1:8000
```

### 3. Frontend

```powershell
cd frontend
npm install
npm run dev -- --host 127.0.0.1 --port 5175
```

Frontend runs at:

```text
http://127.0.0.1:5175
```

## Environment Variables

### Frontend

Create `frontend/.env` from `frontend/.env.example`.

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

For production, the current deployed backend is:

```env
VITE_API_BASE_URL=https://ai-interview-simulator-iu72.onrender.com
```

### Backend

Use `backend/.env.example` as the reference for local setup.

Important production variables:

```env
APP_ENV=production
DATABASE_URL=your-postgres-connection-string
JWT_SECRET=your-strong-random-secret
ALLOWED_ORIGINS=https://your-frontend-url.vercel.app
JWT_EXPIRES_MINUTES=720
SESSION_TTL_SECONDS=7200
RATE_LIMIT_ENABLED=true
CACHE_ENABLED=false
```

## Deployment

### Backend on Render

- Root directory: `backend`
- Runtime: `Python`
- Build command:

```text
pip install -r requirements.txt
```

- Start command:

```text
uvicorn main:app --host 0.0.0.0 --port $PORT --proxy-headers
```

### Frontend on Vercel

- Framework: `Vite`
- Root directory: `frontend`
- Required env:

```env
VITE_API_BASE_URL=https://ai-interview-simulator-iu72.onrender.com
```

### CORS

Backend `ALLOWED_ORIGINS` must include the exact deployed frontend origin, for example:

```env
ALLOWED_ORIGINS=https://ai-interview-simulator-a26hoswav-riyashekhawat14s-projects.vercel.app
```

If you use multiple Vercel deployment URLs, add them comma-separated on one line.

## API Highlights

- `POST /auth/register`
- `POST /auth/login`
- `GET /auth/me`
- `POST /interview/start`
- `POST /interview/next`
- `POST /interview/submit-code`
- `POST /interview/report`
- `GET /reports/history`
- `GET /reports/latest`
- `GET /metrics`
- `GET /health`

## Verified Flow

The current application flow supports:

1. Create an account or sign in
2. Upload a resume
3. Start an interview session
4. Answer general interview questions
5. Continue into the DSA round
6. Submit coding answers
7. Generate and review the final report

## Notes

- Local development can fall back to SQLite if `DATABASE_URL` is not provided.
- The app is designed to degrade gracefully if Ollama is unavailable.
- Browser-based features like microphone access, camera access, speech recognition, and speech playback depend on user permissions and browser support.
- Chrome or Edge usually provide the smoothest experience for voice-related features.

## Scripts

From the repo root:

```powershell
npm run frontend:dev
npm run frontend:build
npm run frontend:lint
npm run backend:dev
npm run backend:smoke
```

## Future Improvements

- Stable custom production domain for the frontend
- Shared Redis cache for multi-instance deployments
- More robust report analytics
- Better admin and monitoring workflows
- Background jobs for heavy AI tasks

## License

Add your preferred license here.
