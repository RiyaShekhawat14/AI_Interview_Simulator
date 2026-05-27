# Frontend

React + Vite client for the AI interview simulator.

## Run

```powershell
npm run dev -- --host 127.0.0.1 --port 5175
```

## Build

```powershell
npm run build
```

## Environment

Create a `.env` from [frontend/.env.example](/c:/Users/hp/OneDrive/Desktop/AI_interview_project/frontend/.env.example) and point `VITE_API_BASE_URL` at your deployed backend.

## Notes

- The frontend expects the backend at `VITE_API_BASE_URL`.
- Default local backend URL is `http://127.0.0.1:8000`.
- Camera, microphone, speech recognition, and text-to-speech are browser-dependent features.
