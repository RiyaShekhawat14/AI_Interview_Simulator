import os
from urllib.parse import urlparse


_PRODUCTION_ENV_NAMES = {"prod", "production"}
_INSECURE_JWT_SECRETS = {
    "",
    "changeme",
    "dev-secret-change-me",
    "replace-with-a-long-random-secret",
    "your-jwt-secret",
}


def app_environment() -> str:
    return os.getenv("APP_ENV", "development").strip().lower() or "development"


def is_production() -> bool:
    return app_environment() in _PRODUCTION_ENV_NAMES


def env_flag(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() not in {"0", "false", "no", "off"}


def _parse_allowed_origins() -> list[str]:
    raw_value = os.getenv("ALLOWED_ORIGINS", "")
    return [origin.strip() for origin in raw_value.split(",") if origin.strip()]


def _looks_local_origin(origin: str) -> bool:
    try:
        parsed = urlparse(origin)
    except Exception:
        return False

    hostname = (parsed.hostname or "").lower()
    return hostname in {"localhost", "127.0.0.1", "0.0.0.0"}


def validate_runtime_config() -> None:
    if not is_production():
        return

    errors: list[str] = []
    warnings: list[str] = []

    database_url = os.getenv("DATABASE_URL", "").strip()
    jwt_secret = os.getenv("JWT_SECRET", "").strip()
    allowed_origins = _parse_allowed_origins()
    llama_api_url = os.getenv("LLAMA_API_URL", "").strip()

    if not database_url:
        errors.append("DATABASE_URL is required in production.")
    elif database_url.startswith("sqlite"):
        errors.append("DATABASE_URL must point to managed Postgres or another production database, not SQLite.")

    if jwt_secret.lower() in _INSECURE_JWT_SECRETS or len(jwt_secret) < 32:
        errors.append("JWT_SECRET must be set to a strong random value with at least 32 characters.")

    if not allowed_origins:
        errors.append("ALLOWED_ORIGINS must include your real frontend URL in production.")
    elif "*" in allowed_origins:
        errors.append("ALLOWED_ORIGINS cannot use '*' in production.")
    elif any(_looks_local_origin(origin) for origin in allowed_origins):
        errors.append("ALLOWED_ORIGINS cannot include localhost-style origins in production.")

    if not os.getenv("REDIS_URL", "").strip():
        warnings.append("REDIS_URL is not set; cache and rate-limit state stay instance-local.")

    if llama_api_url and _looks_local_origin(llama_api_url):
        warnings.append("LLAMA_API_URL points at localhost; confirm Ollama runs on the same deployed host or expect fallback mode.")

    if warnings:
        for message in warnings:
            print(f"[config warning] {message}")

    if errors:
        error_block = "\n".join(f"- {message}" for message in errors)
        raise RuntimeError(f"Production configuration validation failed:\n{error_block}")
