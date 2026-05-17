# Launch Checklist

## Before Deploying

1. Set `ALLOWED_ORIGINS` to your real frontend domain.
2. Set a strong `JWT_SECRET`.
3. Point `DATABASE_URL` at SQLite for local use or managed Postgres for deployment.
4. Confirm Ollama is reachable from the backend host if you want live model responses.
5. Confirm the Python environment includes `openai-whisper`, `torch`, `torchvision`, and `opencv-python`.
6. Set cache TTL values if you want different behavior for local development versus launch traffic.
7. Set `REDIS_URL` if you want shared cache behavior across multiple backend instances.
8. Tune the request rate limit window and max requests for your expected usage pattern.

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

## Interview Talking Points

1. The app now uses real account-based JWT auth instead of a shared secret.
2. Users, interview sessions, and reports now persist in a relational database model.
3. Session TTL cleanup prevents abandoned sessions from accumulating forever.
4. The backend now includes request metrics and short-lived caching so common hot paths are observable and cheaper to serve.
5. The cache layer is Redis-ready, but still falls back to in-memory mode for easy local development.
6. Request logging and rate limiting make the backend feel more like an operated API rather than a local-only prototype.
7. Ollama remains optional because the product degrades gracefully to fallback logic.
8. The next production upgrade would be adding refresh tokens, background jobs, and RBAC/admin controls.
