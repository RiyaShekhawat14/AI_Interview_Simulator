from typing import List
import os
from fastapi import APIRouter, Depends, Query
from fastapi import HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from services.auth_service import get_current_user
from services.cache_service import get_or_set_cached, invalidate_prefix, make_cache_key
from services.db_service import User, get_db
from services.persistence_service import get_latest_report, get_report, list_reports, save_report
from services.report_service import generate_interview_report

router = APIRouter()
REPORT_CACHE_TTL_SECONDS = int(os.getenv("REPORT_CACHE_TTL_SECONDS", "30"))


class QAItem(BaseModel):
    question: str
    answer: str
    emotion: str = "Normal"
    emotion_confidence: float = 0.0
    phase: str = "general"


class CodeExercise(BaseModel):
    question: str
    code: str
    language: str
    evaluation: str = ""
    emotion: str = "Normal"
    emotion_confidence: float = 0.0


class ReportRequest(BaseModel):
    role: str
    company: str
    responses: List[QAItem]
    code_exercises: List[CodeExercise] = []


@router.post("/report")
async def final_report(
    payload: ReportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    combined_responses = [
        {
            "question": item.question,
            "answer": item.answer,
            "emotion": item.emotion,
            "emotion_confidence": item.emotion_confidence,
            "phase": item.phase,
        }
        for item in payload.responses
    ]

    for item in payload.code_exercises:
        combined_responses.append(
            {
                "question": item.question,
                "answer": item.code,
                "language": item.language,
                "evaluation": {"evaluation": item.evaluation},
                "emotion": item.emotion,
                "emotion_confidence": item.emotion_confidence,
                "phase": "dsa",
            }
        )

    report = generate_interview_report(
        responses=combined_responses,
        role=payload.role,
        company=payload.company,
    )
    report_id = save_report(db, report, user_id=current_user.id)
    invalidate_prefix(f"reports:{current_user.id}:")
    return {**report, "report_id": report_id}


@router.get("/reports/history")
async def report_history(
    limit: int = Query(default=10, ge=1, le=50),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key(
        f"reports:{current_user.id}:history",
        {"limit": limit},
    )
    reports = get_or_set_cached(
        cache_key,
        lambda: list_reports(db, current_user.id, limit),
        ttl_seconds=REPORT_CACHE_TTL_SECONDS,
    )
    return {"reports": reports}


@router.get("/reports/latest")
async def latest_report(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    cache_key = make_cache_key(f"reports:{current_user.id}:latest", {"latest": True})
    report = get_or_set_cached(
        cache_key,
        lambda: get_latest_report(db, current_user.id),
        ttl_seconds=REPORT_CACHE_TTL_SECONDS,
    )
    if not report:
        raise HTTPException(status_code=404, detail="No saved reports found")
    return {"report": report}


@router.get("/reports/{report_id}")
async def report_detail(
    report_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    cache_key = make_cache_key(
        f"reports:{current_user.id}:detail",
        {"report_id": report_id},
    )
    report = get_or_set_cached(
        cache_key,
        lambda: get_report(db, report_id, current_user.id),
        ttl_seconds=REPORT_CACHE_TTL_SECONDS,
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    return {"report": report}
