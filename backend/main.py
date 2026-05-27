from fastapi import FastAPI
from fastapi import Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import logging
import os
import sys
import time
from pathlib import Path

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.env_service import load_env_file

load_env_file(Path(__file__).resolve().parent / ".env")

from routes.auth import router as auth_router
from routes.code import router as code_router
from routes.health import router as health_router
from routes.interview import router as interview_router
from routes.metrics import router as metrics_router
from routes.question import router as question_router
from routes.report import router as report_router
from routes.upload import router as upload_router
from services.config_service import validate_runtime_config
from services.db_service import init_database
from services.metrics_service import record_request
from services.rate_limit_service import check_rate_limit

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ai_interview_backend")

def _parse_allowed_origins() -> tuple[list[str], bool]:
    raw_value = os.getenv("ALLOWED_ORIGINS", "*")
    origins = [origin.strip() for origin in raw_value.split(",") if origin.strip()]

    if not origins:
        return ["http://localhost:5173"], True

    if "*" in origins:
        return ["*"], False

    return origins, True


app = FastAPI()

allowed_origins, allow_credentials = _parse_allowed_origins()

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=allow_credentials,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(interview_router)
app.include_router(report_router)
app.include_router(question_router)
app.include_router(code_router)
app.include_router(upload_router)
app.include_router(health_router)
app.include_router(metrics_router)


@app.middleware("http")
async def request_metrics_middleware(request: Request, call_next):
    started = time.perf_counter()
    status_code = 500
    try:
        identity = request.client.host if request.client else "unknown"
        if request.url.path not in {"/health", "/metrics"}:
            allowed, rate_limit = check_rate_limit(identity)
            if not allowed:
                status_code = 429
                logger.warning(
                    "rate_limit_block method=%s path=%s identity=%s remaining=%s",
                    request.method,
                    request.url.path,
                    identity,
                    rate_limit.get("remaining"),
                )
                return JSONResponse(
                    status_code=429,
                    content={
                        "detail": "Rate limit exceeded. Try again shortly.",
                        "rate_limit": rate_limit,
                    },
                )

        response = await call_next(request)
        status_code = response.status_code
        logger.info(
            "request method=%s path=%s status=%s duration_ms=%.2f",
            request.method,
            request.url.path,
            status_code,
            (time.perf_counter() - started) * 1000,
        )
        return response
    finally:
        duration_ms = (time.perf_counter() - started) * 1000
        record_request(request.method, request.url.path, status_code, duration_ms)


@app.on_event("startup")
def startup() -> None:
    validate_runtime_config()
    init_database()


@app.get("/")
def home():
    return {"message": "AI Interview Backend Running"}
