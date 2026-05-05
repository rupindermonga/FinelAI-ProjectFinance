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
_LOGIN_MAX    = int(os.getenv("LOGIN_RATE_LIMIT", "10"))  # 10 failed attempts per window
_DEMO_MAX     = 5            # max demo logins per window per IP
_REGISTER_MAX = 20           # max register attempts per window per IP
_WINDOW_SECONDS = 120        # 2-minute rolling window
_login_attempts: dict  = defaultdict(list)
_demo_attempts: dict   = defaultdict(list)
_register_attempts: dict = defaultdict(list)


def _check_rate_limit(request: Request):
    """Raise 429 if the client IP has too many FAILED login attempts."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _login_attempts[ip] = [t for t in _login_attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(_login_attempts[ip]) >= _LOGIN_MAX:
        raise HTTPException(status_code=429, detail="Too many failed login attempts. Try again in 2 minutes.")


def _record_failed_attempt(request: Request):
    """Record a failed login attempt for rate limiting."""
    ip = request.client.host if request.client else "unknown"
    _login_attempts[ip].append(time.time())


def _check_demo_rate(request: Request):
    """Raise 429 if the client IP has too many demo logins."""
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    _demo_attempts[ip] = [t for t in _demo_attempts[ip] if now - t < _WINDOW_SECONDS]
    if len(_demo_attempts[ip]) >= _DEMO_MAX:
        raise HTTPException(status_code=429, detail="Too many demo requests. Try again in 2 minutes.")
    _demo_attempts[ip].append(now)


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


@router.post("/register")
def register(body: UserCreate, request: Request = None, db: Session = Depends(get_db)):
    """Public registration is disabled. Use Admin → User Management to create accounts."""
    raise HTTPException(status_code=403, detail="Public registration is disabled. Contact your admin for an account.")


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


@router.post("/demo", response_model=Token)
def demo_login(request: Request = None, db: Session = Depends(get_db)):
    """One-click demo login — returns a token for the pre-seeded demo account.
    Requires DEMO_ENABLED=true in env. Run create_demo.py first to seed the account."""
    _check_demo_rate(request)
    if os.getenv("DEMO_ENABLED", "false").strip().lower() not in ("1", "true", "yes"):
        raise HTTPException(status_code=403, detail="Demo mode is not enabled on this instance.")
    user = db.query(User).filter(User.username == "demo").first()
    if not user:
        raise HTTPException(status_code=503, detail="Demo account not initialized. Contact the administrator.")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Demo account is disabled.")
    token = create_token(user.id)
    return Token(access_token=token, token_type="bearer", user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
def me(current_user: User = Depends(get_current_user)):
    return current_user


@router.put("/change-password")
def change_password(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Change own password. Requires current_password and new_password."""
    current_pw = body.get("current_password", "")
    new_pw = body.get("new_password", "")
    if not current_pw or not new_pw:
        raise HTTPException(status_code=400, detail="current_password and new_password required")
    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="New password must be at least 8 characters")
    if not pwd_context.verify(current_pw, current_user.hashed_password):
        raise HTTPException(status_code=401, detail="Current password is incorrect")
    current_user.hashed_password = pwd_context.hash(new_pw)
    db.commit()
    return {"message": "Password changed successfully"}
