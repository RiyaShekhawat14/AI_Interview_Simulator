from fastapi import APIRouter, Depends
import os
from pydantic import BaseModel
from services.cache_service import get_or_set_cached, make_cache_key
from services.auth_service import get_current_user
from services.db_service import User
from services.code_service import evaluate_code

router = APIRouter()
CODE_CACHE_TTL_SECONDS = int(os.getenv("CODE_CACHE_TTL_SECONDS", "300"))


class CodeEvalRequest(BaseModel):
    question: str
    code: str
    language: str


@router.post("/evaluate-code")
async def evaluate_code_route(payload: CodeEvalRequest, current_user: User = Depends(get_current_user)):
    cache_key = make_cache_key(
        "code-eval",
        {
            "user_id": current_user.id,
            "question": payload.question,
            "code": payload.code,
            "language": payload.language,
        },
    )
    return get_or_set_cached(
        cache_key,
        lambda: evaluate_code(payload.question, payload.code, payload.language),
        ttl_seconds=CODE_CACHE_TTL_SECONDS,
    )
