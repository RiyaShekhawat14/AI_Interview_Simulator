import os
import time

import requests


LLAMA_API_URL = os.getenv("LLAMA_API_URL", "http://127.0.0.1:11434/api/generate")
LLAMA_MODEL = os.getenv("LLAMA_MODEL", "mistral:latest")
LLAMA_FALLBACK_MODEL = os.getenv("LLAMA_FALLBACK_MODEL", "llama3:8b")
LLAMA_TIMEOUT_SECONDS = int(os.getenv("LLAMA_TIMEOUT_SECONDS", "45"))
LLAMA_CONNECT_TIMEOUT_SECONDS = float(os.getenv("LLAMA_CONNECT_TIMEOUT_SECONDS", "1.5"))
LLAMA_DISABLE_COOLDOWN_SECONDS = max(5, int(os.getenv("LLAMA_DISABLE_COOLDOWN_SECONDS", "30")))
DEFAULT_OLLAMA_URLS = [
    "http://127.0.0.1:11434/api/generate",
    "http://127.0.0.1:11435/api/generate",
]

_disabled_until = 0.0


def _request_timeout(timeout: int | float | None) -> tuple[float, float]:
    read_timeout = float(timeout or LLAMA_TIMEOUT_SECONDS)
    return (LLAMA_CONNECT_TIMEOUT_SECONDS, read_timeout)


def _candidate_urls() -> list[str]:
    urls = [LLAMA_API_URL]
    if not os.getenv("LLAMA_API_URL"):
        urls.extend([url for url in DEFAULT_OLLAMA_URLS if url not in urls])
    return urls


def ollama_circuit_state() -> dict[str, float | bool | int]:
    now = time.time()
    disabled = _disabled_until > now
    return {
        "disabled": disabled,
        "cooldown_seconds": LLAMA_DISABLE_COOLDOWN_SECONDS,
        "retry_in_seconds": max(int(round(_disabled_until - now)), 0) if disabled else 0,
    }


def reset_ollama_circuit(force: bool = False) -> None:
    global _disabled_until
    if force or _disabled_until <= time.time():
        _disabled_until = 0.0


def _trip_circuit() -> None:
    global _disabled_until
    _disabled_until = time.time() + LLAMA_DISABLE_COOLDOWN_SECONDS


def _ensure_circuit_open() -> None:
    state = ollama_circuit_state()
    if state["disabled"]:
        raise Exception(
            "Ollama temporarily disabled after a connection failure. "
            f"Retry in about {state['retry_in_seconds']}s."
        )


def call_ollama(
    prompt: str,
    model: str = LLAMA_MODEL,
    temperature: float = 0.7,
    num_predict: int = 60,
    timeout: int | float | None = None,
) -> str:
    _ensure_circuit_open()

    last_error = None
    for url in _candidate_urls():
        try:
            response = requests.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": num_predict,
                    },
                },
                timeout=_request_timeout(timeout),
            )
            if response.status_code != 200:
                last_error = Exception(f"Ollama status {response.status_code} at {url}: {response.text[:120]}")
                continue

            payload = response.json()
            text = (payload.get("response") or payload.get("generated_text") or payload.get("result") or "").strip()
            if text:
                reset_ollama_circuit(force=True)
                return text
            last_error = Exception(f"Empty Ollama response from {url}")
        except requests.RequestException as error:
            last_error = error

    if isinstance(last_error, requests.RequestException):
        _trip_circuit()
    raise Exception(last_error or "Unable to connect to Ollama on any configured port.")


def call_ollama_with_model_fallback(
    prompt: str,
    temperature: float = 0.7,
    num_predict: int = 60,
    timeout: int | float | None = None,
) -> tuple[str, str]:
    try:
        return call_ollama(
            prompt,
            model=LLAMA_MODEL,
            temperature=temperature,
            num_predict=num_predict,
            timeout=timeout,
        ), LLAMA_MODEL
    except Exception as primary_error:
        if LLAMA_FALLBACK_MODEL and LLAMA_FALLBACK_MODEL != LLAMA_MODEL:
            try:
                return call_ollama(
                    prompt,
                    model=LLAMA_FALLBACK_MODEL,
                    temperature=temperature,
                    num_predict=num_predict,
                    timeout=timeout,
                ), LLAMA_FALLBACK_MODEL
            except Exception:
                pass
        raise primary_error
