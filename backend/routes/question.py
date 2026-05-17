from fastapi import APIRouter, Depends
import os
from services.cache_service import get_or_set_cached, make_cache_key
from services.auth_service import get_current_user
from services.db_service import User
from services.question_service import generate_question_result
import services.resume_store as store

router = APIRouter()
QUESTION_CACHE_TTL_SECONDS = int(os.getenv("QUESTION_CACHE_TTL_SECONDS", "180"))


@router.post("/question")
async def get_question(
    role: str,
    company: str,
    answer: str = "",
    asked: str = "",
    category: str = "general",
    resume_text: str = "",
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    asked_questions = [q.strip() for q in asked.split("||") if q.strip()]
    active_resume_text = (resume_text or "").strip() or store.resume_text

    cache_key = make_cache_key(
        "question",
        {
            "user_id": current_user.id,
            "role": role,
            "company": company,
            "answer": answer,
            "asked_questions": asked_questions,
            "category": category,
            "resume_text": active_resume_text[:500],
        },
    )
    result = get_or_set_cached(
        cache_key,
        lambda: generate_question_result(
            active_resume_text,
            role,
            company,
            answer,
            asked_questions,
            category,
        ),
        ttl_seconds=QUESTION_CACHE_TTL_SECONDS,
    )

    return result
