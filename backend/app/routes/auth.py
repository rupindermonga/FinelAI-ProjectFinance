from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
from jose import jwt
from passlib.context import CryptContext
import os
import time

from ..database import get_db
from ..models import User
from ..schemas import UserCreate, UserLogin, UserOut, Token
from ..dependencies import get_current_user, SECRET_KEY, ALGORITHM

router = APIRouter(prefix="/api/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
EXPIRE_MINUTES = int(os.getenv("JWT_EXPIRE_MINUTES", "10080"))

# ── In-memory rate limiter (separate buckets per endpoint) ───────────────────
_LOGIN_MAX = int(os.getenv("LOGIN_RATE_LIMIT", "30"))  # max failed login attempts per window per IP
_REGISTER_MAX = 20          # max register attempts per window per IP
_WINDOW_SECONDS = 120       # 2-minute window (balances security vs QA stability)
_login_attempts: dict = defaultdict(list)
_register_attempts: dict = defaultdict(list)


def _check_rate_limit(request: Request):
    """Raise 429 if the client IP has too many FAILED login attempts."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(_login_attempts[ip]) >= _LOGIN_MAX:
        raise HTTPException(status_code=429, detail="Too many attempts. Please try again later.")


def _record_failed_attempt(request: Request):
    """Record a failed login attempt for rate limiting."""
    ip = request.client.host if request.client else "unknown"
    _login_attempts[ip].append(time.time())


def _check_register_rate(request: Request):
    """Soft rate limit for registration — prevents mass account creation."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _register_attempts[ip] = [t for t in _register_attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(_register_attempts[ip]) >= _REGISTER_MAX:
        raise HTTPException(status_code=429, detail="Too many registration attempts. Please try again later.")
    _register_attempts[ip].append(now)


def create_token(user_id: int) -> str:
    expire = datetime.utcnow() + timedelta(minutes=EXPIRE_MINUTES)
    return jwt.encode({"sub": str(user_id), "exp": expire}, SECRET_KEY, algorithm=ALGORITHM)


@router.post("/register", response_model=Token)
def register(body: UserCreate, request: Request = None, db: Session = Depends(get_db)):
    _check_register_rate(request)
    if db.query(User).filter(User.username == body.username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=body.username,
        email=body.email,
        hashed_password=pwd_context.hash(body.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Seed default columns for new user
    from ..seed_columns import seed_default_columns
    seed_default_columns(db, user.id)

    token = create_token(user.id)
    return Token(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.post("/login", response_model=Token)
def login(body: UserLogin, request: Request = None, db: Session = Depends(get_db)):
    _check_rate_limit(request)
    user = db.query(User).filter(User.username == body.username).first()
    if not user or not pwd_context.verify(body.password, user.hashed_password):
        _record_failed_attempt(request)
        raise HTTPException(status_code=401, detail="Invalid username or password")
    # Successful login — clear failed attempts for this IP
    ip = request.client.host if request and request.client else "unknown"
    _login_attempts.pop(ip, None)

    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account is disabled")

    from ..seed_columns import patch_existing_user_columns
    patch_existing_user_columns(db, user.id)

    from ..seed_project import seed_project_finance
    seed_project_finance(db, user.id)

    token = create_token(user.id)
    return Token(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user
