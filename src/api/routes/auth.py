"""
src/api/routes/auth.py
POST /api/auth/register  – create account with bcrypt password
POST /api/auth/login     – verify credentials, return JWT
"""
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlmodel import Session, select

from src.database.connection import get_session
from src.models import User
from src.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterReq(BaseModel):
    model_config = ConfigDict(extra="forbid")

    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=6, max_length=128)


class LoginReq(BaseModel):
    username: str = Field(min_length=3, max_length=50)
    password: str = Field(min_length=1, max_length=128)


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: int
    username: str
    role: str
    has_resume: bool


@router.post("/register", response_model=AuthResponse, status_code=201)
def register(req: RegisterReq, session: Session = Depends(get_session)):
    existing = session.exec(select(User).where(User.username == req.username)).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(username=req.username, hashed_password=hash_password(req.password), role="candidate")
    session.add(user)
    session.commit()
    session.refresh(user)

    token = create_access_token(user.id, user.username, user.role)
    return AuthResponse(access_token=token, user_id=user.id, username=user.username, role=user.role, has_resume=False)


@router.post("/login", response_model=AuthResponse)
def login(req: LoginReq, session: Session = Depends(get_session)):
    user = session.exec(select(User).where(User.username == req.username)).first()

    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    stored_hash = (user.hashed_password or "").strip()
    try:
        password_valid = bool(stored_hash) and verify_password(req.password, stored_hash)
    except ValueError:
        password_valid = False
    if not password_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    from src.models import Resume
    from sqlmodel import select as sel
    has_resume = session.exec(sel(Resume).where(Resume.user_id == user.id)).first() is not None

    token = create_access_token(user.id, user.username, user.role)
    return AuthResponse(access_token=token, user_id=user.id, username=user.username, role=user.role, has_resume=has_resume)
