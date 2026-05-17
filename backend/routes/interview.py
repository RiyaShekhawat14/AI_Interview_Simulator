from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
import logging
import mimetypes
import os
import tempfile
import time
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from services.auth_service import get_current_user
from services.cache_service import invalidate_prefix
from services.code_service import evaluate_code as evaluate_code_service
from services.db_service import User, get_db
from services.emotion_service import detect_emotion_bytes
from services.persistence_service import (
    build_session_state,
    delete_expired_sessions,
    delete_session,
    load_session,
    save_report,
    save_session,
)
from services.question_service import generate_question_result
from services.report_service import generate_interview_report
from services.speech_service import speech_model_available, transcribe_audio

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

GENERAL_QUESTION_LIMIT = 5
DSA_QUESTION_LIMIT = 2
SESSION_TTL_SECONDS = int(os.getenv("SESSION_TTL_SECONDS", "7200"))

interview_sessions: dict[str, dict[str, Any]] = {}


def _normalize_emotion_result(emotion_result: Any) -> dict[str, Any]:
    if isinstance(emotion_result, dict):
        emotion = emotion_result.get("emotion", "Normal")
        confidence = float(emotion_result.get("confidence", 0.0) or 0.0)
        status = emotion_result.get("status", "unknown")
        return {
            "emotion": emotion,
            "confidence": confidence,
            "status": status,
            "reliable": confidence >= 0.5,
            "raw": emotion_result,
        }

    return {
        "emotion": str(emotion_result or "Normal"),
        "confidence": 0.0,
        "status": "parse_error",
        "reliable": False,
        "raw": {"emotion": str(emotion_result or "Normal")},
    }


def _persist_session(db: Session, session_id: str, user_id: int, session: dict[str, Any]) -> None:
    save_session(db, session_id, user_id, session)


def _prune_expired_sessions(db: Session) -> None:
    now = int(time.time())
    expired_ids = [
        session_id
        for session_id, session in interview_sessions.items()
        if now - int(session.get("last_activity", session.get("start_time", now)) or now) > SESSION_TTL_SECONDS
    ]
    for session_id in expired_ids:
        interview_sessions.pop(session_id, None)
    delete_expired_sessions(db, SESSION_TTL_SECONDS)


def _get_session(db: Session, session_id: str, user_id: int) -> dict[str, Any]:
    _prune_expired_sessions(db)
    session = interview_sessions.get(session_id)
    if not session:
        session = load_session(db, session_id, user_id)
        if session:
            interview_sessions[session_id] = session
    if not session:
        raise HTTPException(status_code=404, detail="Interview session not found")
    session["last_activity"] = int(time.time())
    _persist_session(db, session_id, user_id, session)
    return session


def _append_text_response(session: dict[str, Any], answer: str, emotion_payload: dict[str, Any]) -> None:
    current_question = session.get("current_question")
    if not current_question or not answer.strip():
        return

    session["responses"].append(
        {
            "question": current_question,
            "answer": answer.strip(),
            "emotion": emotion_payload["emotion"],
            "emotion_confidence": emotion_payload["confidence"],
            "emotion_status": emotion_payload["status"],
            "phase": session.get("phase", "general"),
            "timestamp": time.time(),
        }
    )
    session["emotion_history"].append(emotion_payload)


def _next_phase_payload(session: dict[str, Any], question_data: dict[str, Any]) -> dict[str, Any]:
    payload = {
        "question": question_data["question"],
        "phase": session["phase"],
        "question_number": session["question_count"] + session["dsa_count"],
        "type": "text",
        "question_source": question_data.get("source", "fallback"),
        "question_model": question_data.get("model", "unknown"),
        "question_error": question_data.get("error", ""),
    }

    if session["phase"] == "dsa":
        payload["type"] = "code"
        payload["language"] = session["preferred_language"]

    return payload


@router.post("/interview/start")
def start_interview(
    role: str = Form(...),
    company: str = Form(...),
    resume_text: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _prune_expired_sessions(db)
    session_id = uuid4().hex
    session = build_session_state(role, company, resume_text)
    interview_sessions[session_id] = session
    _persist_session(db, session_id, current_user.id, session)
    return {"session_id": session_id}


@router.post("/interview/next")
def get_next_question(
    session_id: str = Form(...),
    last_answer: str = Form(""),
    emotion: str = Form("Normal"),
    emotion_confidence: float = Form(0.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)

    if session["phase"] == "general" and last_answer.strip():
        _append_text_response(
            session,
            last_answer,
            {
                "emotion": emotion or "Normal",
                "confidence": emotion_confidence,
                "status": "client_capture",
                "reliable": emotion_confidence >= 0.5,
                "raw": {},
            },
        )

    if session["phase"] == "general":
        if session["question_count"] < GENERAL_QUESTION_LIMIT:
            question_data = generate_question_result(
                session["resume_text"],
                session["role"],
                session["company"],
                last_answer,
                session["asked_questions"],
                "general",
            )
            session["question_count"] += 1
            session["current_question"] = question_data["question"]
            session["asked_questions"].append(question_data["question"])
            _persist_session(db, session_id, current_user.id, session)
            return _next_phase_payload(session, question_data)

        session["phase"] = "dsa"
        _persist_session(db, session_id, current_user.id, session)

    if session["phase"] == "dsa":
        if session["dsa_count"] < DSA_QUESTION_LIMIT:
            question_data = generate_question_result(
                session["resume_text"],
                session["role"],
                session["company"],
                last_answer,
                session["asked_questions"],
                "dsa",
            )
            session["dsa_count"] += 1
            session["current_question"] = question_data["question"]
            session["asked_questions"].append(question_data["question"])
            _persist_session(db, session_id, current_user.id, session)
            return _next_phase_payload(session, question_data)

        session["phase"] = "complete"
        _persist_session(db, session_id, current_user.id, session)

    return {"question": None, "phase": "complete", "type": "report"}


@router.post("/interview/submit-code")
def submit_code_answer(
    session_id: str = Form(...),
    code: str = Form(...),
    language: str = Form("python"),
    emotion: str = Form("Normal"),
    emotion_confidence: float = Form(0.0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    if session["phase"] != "dsa":
        raise HTTPException(status_code=400, detail="Code submission is only allowed during the DSA round")

    question = session.get("current_question", "")
    evaluation = evaluate_code_service(question, code, language)

    session["preferred_language"] = language
    session["responses"].append(
        {
            "question": question,
            "answer": code.strip(),
            "language": language,
            "evaluation": evaluation,
            "emotion": emotion or "Normal",
            "emotion_confidence": emotion_confidence,
            "emotion_status": "client_capture",
            "phase": "dsa",
            "timestamp": time.time(),
        }
    )
    session["emotion_history"].append(
        {
            "emotion": emotion or "Normal",
            "confidence": emotion_confidence,
            "status": "client_capture",
            "reliable": emotion_confidence >= 0.5,
        }
    )
    _persist_session(db, session_id, current_user.id, session)
    return evaluation


@router.post("/interview/report")
def get_interview_report(
    session_id: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = _get_session(db, session_id, current_user.id)
    report = generate_interview_report(
        responses=session["responses"],
        role=session["role"],
        company=session["company"],
        started_at=session["start_time"],
        finished_at=time.time(),
    )
    report_id = save_report(db, report, user_id=current_user.id, session_id=session_id)
    invalidate_prefix(f"reports:{current_user.id}:")
    interview_sessions.pop(session_id, None)
    delete_session(db, session_id, current_user.id)
    return {**report, "report_id": report_id}


@router.post("/speech-to-text")
async def speech_to_text(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    original_name = file.filename or "recording"
    guessed_extension = os.path.splitext(original_name)[1]
    if not guessed_extension:
        guessed_extension = mimetypes.guess_extension(file.content_type or "") or ".webm"

    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=guessed_extension)
    file_path = temp_file.name
    try:
        logger.info("Receiving audio file: %s (%s)", original_name, file.content_type)
        audio_bytes = await file.read()
        temp_file.write(audio_bytes)
        temp_file.close()

        if not audio_bytes:
            return {
                "text": "",
                "available": speech_model_available(),
                "warning": "The uploaded audio file was empty.",
            }

        available = speech_model_available()
        text = transcribe_audio(file_path)
        response = {"text": text, "available": available}
        if available and not text:
            response["warning"] = "Transcription completed but no speech was recognized."
        if not available:
            response["warning"] = "Speech model is unavailable in the current Python environment."
        return response
    except Exception as error:
        logger.error("Error in speech-to-text: %s", error, exc_info=True)
        return {"text": "", "error": str(error)}
    finally:
        temp_file.close()
        if os.path.exists(file_path):
            os.remove(file_path)


@router.post("/detect-emotion")
async def detect_emotion_api(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    _ = current_user
    try:
        image_bytes = await file.read()
        result = _normalize_emotion_result(detect_emotion_bytes(image_bytes))
        return {
            "emotion": result["emotion"],
            "confidence": result["confidence"],
            "status": result["status"],
            "reliable": result["reliable"],
            "details": result["raw"],
        }
    except Exception as error:
        logger.error("Error in emotion detection: %s", error, exc_info=True)
        return {
            "emotion": "Normal",
            "confidence": 0.0,
            "status": f"error: {error}",
            "reliable": False,
            "details": {},
        }
