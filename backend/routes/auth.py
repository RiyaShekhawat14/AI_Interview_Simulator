from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from services.auth_service import authenticate_user, create_access_token, get_current_user, hash_password
from services.db_service import User, get_db
from services.persistence_service import create_user


router = APIRouter(prefix="/auth", tags=["auth"])


class RegisterRequest(BaseModel):
    email: str
    full_name: str
    password: str


class LoginRequest(BaseModel):
    email: str
    password: str


def _user_payload(user: User) -> dict:
    return {"id": user.id, "email": user.email, "full_name": user.full_name}


@router.post("/register")
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    email = payload.email.strip().lower()
    if len(payload.password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters long")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="A valid email address is required")
    if not payload.full_name.strip():
        raise HTTPException(status_code=400, detail="Full name is required")

    existing = db.scalar(select(User).where(User.email == email))
    if existing:
        raise HTTPException(status_code=409, detail="An account already exists for this email")

    user = create_user(
        db,
        email=email,
        full_name=payload.full_name,
        password_hash=hash_password(payload.password),
    )
    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_payload(user)}


@router.post("/login")
def login(payload: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate_user(db, payload.email, payload.password)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    token = create_access_token(user)
    return {"access_token": token, "token_type": "bearer", "user": _user_payload(user)}


@router.get("/me")
def me(current_user: User = Depends(get_current_user)):
    return {"user": _user_payload(current_user)}
