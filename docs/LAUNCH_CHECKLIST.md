# Launch Checklist

## Before Deploying

1. Set `APP_ENV=production` on the backend host.
2. Set `ALLOWED_ORIGINS` to your real frontend domain. Do not use `*` or localhost in production.
3. Set a strong `JWT_SECRET` with at least 32 random characters.
4. Point `DATABASE_URL` at a managed Postgres instance for deployment. Keep SQLite only for local development.
5. Set `VITE_API_BASE_URL` in the frontend to your deployed backend URL.
6. Confirm Ollama is reachable from the backend host if you want live model responses.
7. Confirm the Python environment includes `openai-whisper`, `torch`, `torchvision`, and `opencv-python`.
8. Set cache TTL values if you want different behavior for local development versus launch traffic.
9. Set `REDIS_URL` if you want shared cache behavior across multiple backend instances.
10. Tune the request rate limit window and max requests for your expected usage pattern.
11. Set `LLAMA_CONNECT_TIMEOUT_SECONDS` and `LLAMA_DISABLE_COOLDOWN_SECONDS` if Ollama is optional in production and you want fallback mode to trigger quickly.
12. If you deploy multiple backend instances, set `REDIS_URL` so cache and rate limits are shared across nodes.
13. Rotate any secrets that may have ever been committed locally before publishing the repository.

## Required Replacements

- `.env.example`: replace local placeholder values if you use it as your compose/env source.
- `backend/.env.example`: replace `JWT_SECRET`, `DATABASE_URL`, and `ALLOWED_ORIGINS` before using it for a real deploy.
- `frontend/.env.example`: replace `VITE_API_BASE_URL` with your deployed backend URL.
- `render.yaml`: replace `https://your-frontend-domain.vercel.app` with your real frontend domain before deploying from this template.

## Smoke Tests

1. Open `/health` and confirm `backend: true`.
2. Check whether `ollama` is `true` or intentionally running in fallback mode.
3. Confirm `auth_enabled` and `persistence` match your intended setup.
4. Open `/metrics` and confirm request counters and cache stats are present.
5. Open `/ops` in the frontend and confirm the dashboard reflects backend metrics.
6. Register a user through `/auth/register` or the frontend auth page.
7. Upload a real PDF resume.
8. Complete one short interview and confirm a report is generated.
9. Hit `GET /reports/history` and confirm the saved report appears.
10. Run `npm run backend:smoke` and confirm the smoke test passes before promoting the release.
11. Run `npm --prefix frontend run lint` and `npm --prefix frontend run build`.
12. Run `docker compose build` and confirm both production images build cleanly.

## Interview Talking Points

1. The app now uses real account-based JWT auth instead of a shared secret.
2. Users, interview sessions, and reports now persist in a relational database model.
3. Session TTL cleanup prevents abandoned sessions from accumulating forever.
4. The backend now includes request metrics and short-lived caching so common hot paths are observable and cheaper to serve.
5. The cache layer is Redis-ready, but still falls back to in-memory mode for easy local development.
6. Request logging and rate limiting make the backend feel more like an operated API rather than a local-only prototype.
7. Ollama remains optional because the product degrades gracefully to fallback logic.
8. The next production upgrade would be adding refresh tokens, background jobs, and RBAC/admin controls.
