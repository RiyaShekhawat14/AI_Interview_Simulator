from fastapi import APIRouter
import time
import os
from services.cache_service import get_or_set_cached, make_cache_key, cache_stats
from services.ollama_service import ollama_circuit_state
from services.persistence_service import persistence_enabled
from services.question_service import check_ollama
from services.question_service import LLAMA_API_URL, LLAMA_MODEL

router = APIRouter()
HEALTH_CACHE_TTL_SECONDS = int(os.getenv("HEALTH_CACHE_TTL_SECONDS", "15"))

@router.get("/health")
def health_check():
    status = {
        "backend": True,
        "ollama": False,
        "ollama_model": LLAMA_MODEL,
        "ollama_url": LLAMA_API_URL,
        "auth_enabled": True,
        "persistence": "database" if persistence_enabled() else "memory",
    }
    try:
        cache_key = make_cache_key("health:ollama", {"model": LLAMA_MODEL, "url": LLAMA_API_URL})

        def load_sample():
            started = time.time()
            sample = check_ollama()
            return {
                "sample": sample,
                "latency_ms": int(round((time.time() - started) * 1000)),
            }

        health_payload = get_or_set_cached(
            cache_key,
            load_sample,
            ttl_seconds=HEALTH_CACHE_TTL_SECONDS,
        )
        status["ollama"] = True
        status["ollama_sample"] = health_payload["sample"]
        status["ollama_latency_ms"] = health_payload["latency_ms"]
    except Exception as error:
        status["ollama_error"] = str(error)
    status["ollama_circuit"] = ollama_circuit_state()
    status["cache"] = cache_stats()
    return status
