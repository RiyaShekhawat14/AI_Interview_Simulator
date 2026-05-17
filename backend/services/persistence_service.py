import time
from uuid import uuid4

from sqlalchemy import delete, desc, select
from sqlalchemy.orm import Session

from services.db_service import (
    InterviewReport,
    InterviewSession,
    User,
    deserialize_json,
    serialize_json,
)


def init_persistence() -> None:
    return None


def persistence_enabled() -> bool:
    return True


def build_session_state(role: str, company: str, resume_text: str, preferred_language: str = "python") -> dict:
    now = int(time.time())
    return {
        "role": role.strip(),
        "company": company.strip(),
        "resume_text": resume_text.strip(),
        "phase": "general",
        "question_count": 0,
        "dsa_count": 0,
        "responses": [],
        "asked_questions": [],
        "emotion_history": [],
        "preferred_language": preferred_language,
        "current_question": "",
        "start_time": now,
        "last_activity": now,
    }


def save_session(db: Session, session_id: str, user_id: int, session: dict) -> None:
    record = db.scalar(
        select(InterviewSession).where(
            InterviewSession.session_id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    if not record:
        record = InterviewSession(
            session_id=session_id,
            user_id=user_id,
            role=session.get("role", ""),
            company=session.get("company", ""),
            resume_text=session.get("resume_text", ""),
        )
        db.add(record)

    record.user_id = user_id
    record.role = session.get("role", "")
    record.company = session.get("company", "")
    record.resume_text = session.get("resume_text", "")
    record.phase = session.get("phase", "general")
    record.question_count = int(session.get("question_count", 0) or 0)
    record.dsa_count = int(session.get("dsa_count", 0) or 0)
    record.responses_json = serialize_json(session.get("responses", []))
    record.asked_questions_json = serialize_json(session.get("asked_questions", []))
    record.emotion_history_json = serialize_json(session.get("emotion_history", []))
    record.preferred_language = session.get("preferred_language", "python")
    record.current_question = session.get("current_question", "")
    record.start_time = int(session.get("start_time", int(time.time())) or int(time.time()))
    record.last_activity = int(session.get("last_activity", int(time.time())) or int(time.time()))
    db.commit()


def load_session(db: Session, session_id: str, user_id: int) -> dict | None:
    record = db.scalar(
        select(InterviewSession).where(
            InterviewSession.session_id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    if not record:
        return None

    return {
        "role": record.role,
        "company": record.company,
        "resume_text": record.resume_text,
        "phase": record.phase,
        "question_count": record.question_count,
        "dsa_count": record.dsa_count,
        "responses": deserialize_json(record.responses_json, []),
        "asked_questions": deserialize_json(record.asked_questions_json, []),
        "emotion_history": deserialize_json(record.emotion_history_json, []),
        "preferred_language": record.preferred_language,
        "current_question": record.current_question,
        "start_time": record.start_time,
        "last_activity": record.last_activity,
    }


def delete_session(db: Session, session_id: str, user_id: int) -> None:
    db.execute(
        delete(InterviewSession).where(
            InterviewSession.session_id == session_id,
            InterviewSession.user_id == user_id,
        )
    )
    db.commit()


def delete_expired_sessions(db: Session, ttl_seconds: int) -> None:
    cutoff = int(time.time()) - ttl_seconds
    db.execute(delete(InterviewSession).where(InterviewSession.last_activity < cutoff))
    db.commit()


def save_report(db: Session, report: dict, user_id: int, session_id: str | None = None) -> str:
    report_id = uuid4().hex
    record = InterviewReport(
        report_id=report_id,
        user_id=user_id,
        session_id=session_id,
        role=report.get("role", ""),
        company=report.get("company", ""),
        overall_score=int(report.get("overall_score", 0) or 0),
        assessment=report.get("assessment", ""),
        response_count=int(report.get("response_count", 0) or 0),
        duration_seconds=int(report.get("duration_seconds", 0) or 0),
        report_json=serialize_json(report),
    )
    db.add(record)
    db.commit()
    return report_id


def list_reports(db: Session, user_id: int, limit: int = 10) -> list[dict]:
    safe_limit = max(1, min(int(limit or 10), 50))
    records = db.scalars(
        select(InterviewReport)
        .where(InterviewReport.user_id == user_id)
        .order_by(desc(InterviewReport.created_at))
        .limit(safe_limit)
    ).all()
    return [
        {
            "report_id": record.report_id,
            "session_id": record.session_id,
            "role": record.role,
            "company": record.company,
            "overall_score": record.overall_score,
            "assessment": record.assessment,
            "response_count": record.response_count,
            "duration_seconds": record.duration_seconds,
            "created_at": record.created_at.isoformat(),
        }
        for record in records
    ]


def get_report(db: Session, report_id: str, user_id: int) -> dict | None:
    record = db.scalar(
        select(InterviewReport).where(
            InterviewReport.report_id == report_id,
            InterviewReport.user_id == user_id,
        )
    )
    return deserialize_json(record.report_json, None) if record else None


def get_latest_report(db: Session, user_id: int) -> dict | None:
    record = db.scalar(
        select(InterviewReport)
        .where(InterviewReport.user_id == user_id)
        .order_by(desc(InterviewReport.created_at))
        .limit(1)
    )
    return deserialize_json(record.report_json, None) if record else None


def create_user(db: Session, email: str, full_name: str, password_hash: str) -> User:
    user = User(email=email.strip().lower(), full_name=full_name.strip(), password_hash=password_hash)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user
