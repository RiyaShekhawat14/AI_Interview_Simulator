import json
import os
import time
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
import tempfile

from sqlalchemy import DateTime, ForeignKey, Integer, Text, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, sessionmaker


def _default_database_url() -> str:
    default_path = Path(tempfile.gettempdir()) / "ai_interview_app" / "app.db"
    return f"sqlite:///{default_path.as_posix()}"


DATABASE_URL = os.getenv("DATABASE_URL", _default_database_url())
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, future=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    email: Mapped[str] = mapped_column(Text, unique=True, index=True)
    full_name: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    sessions: Mapped[list["InterviewSession"]] = relationship(back_populates="user")
    reports: Mapped[list["InterviewReport"]] = relationship(back_populates="user")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"

    session_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    role: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(Text)
    resume_text: Mapped[str] = mapped_column(Text, default="")
    phase: Mapped[str] = mapped_column(Text, default="general")
    question_count: Mapped[int] = mapped_column(Integer, default=0)
    dsa_count: Mapped[int] = mapped_column(Integer, default=0)
    responses_json: Mapped[str] = mapped_column(Text, default="[]")
    asked_questions_json: Mapped[str] = mapped_column(Text, default="[]")
    emotion_history_json: Mapped[str] = mapped_column(Text, default="[]")
    preferred_language: Mapped[str] = mapped_column(Text, default="python")
    current_question: Mapped[str] = mapped_column(Text, default="")
    start_time: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))
    last_activity: Mapped[int] = mapped_column(Integer, default=lambda: int(time.time()))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user: Mapped[User] = relationship(back_populates="sessions")


class InterviewReport(Base):
    __tablename__ = "interview_reports"

    report_id: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    session_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    role: Mapped[str] = mapped_column(Text)
    company: Mapped[str] = mapped_column(Text)
    overall_score: Mapped[int] = mapped_column(Integer, default=0)
    assessment: Mapped[str] = mapped_column(Text, default="")
    response_count: Mapped[int] = mapped_column(Integer, default=0)
    duration_seconds: Mapped[int] = mapped_column(Integer, default=0)
    report_json: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    user: Mapped[User] = relationship(back_populates="reports")


def init_database() -> None:
    if DATABASE_URL.startswith("sqlite:///"):
        db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
        db_path.parent.mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def serialize_json(value) -> str:
    return json.dumps(value)


def deserialize_json(value: str, default):
    if not value:
        return default
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return default
