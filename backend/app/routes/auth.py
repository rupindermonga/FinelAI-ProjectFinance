from fastapi import APIRouter, Depends, HTTPException, status, Request, BackgroundTasks
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from collections import defaultdict
from jose import jwt
from passlib.context import CryptContext
import os, time, secrets

from ..database import get_db
from ..models import User, OrganizationMember, Organization, PasswordResetToken, OrgInvitation
from ..schemas import UserCreate, UserLogin, UserOut, Token
from ..dependencies import get_current_user, SECRET_KEY, ALGORITHM
from .audit import log as audit_log


def _user_orgs(user_id: int, db: Session) -> list:
    """Return list of orgs the user belongs to (for login response)."""
    memberships = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == user_id, OrganizationMember.is_active == True)
        .order_by(OrganizationMember.created_at)
        .all()
    )
    result = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id, Organization.is_active == True).first()
        if org:
            result.append({
                "id": org.id, "name": org.name, "slug": org.slug,
                "plan": org.plan, "role": m.role,
                "is_active": org.is_active, "created_at": org.created_at,
            })
    return result

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
def register(body: dict, request: Request = None, db: Session = Depends(get_db)):
    """Public registration is disabled. Use Admin → User Management to create accounts."""
    raise HTTPException(status_code=403, detail="Public registration is disabled. Contact your admin for an account.")


@router.post("/login", response_model=Token)
def login(body: UserLogin, request: Request = None, db: Session = Depends(get_db)):
    _check_rate_limit(request)
    identifier = body.username.strip()
    user = db.query(User).filter(
        (User.username == identifier) | (User.email == identifier)
    ).first()
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

    from ..seed_org import ensure_user_org
    ensure_user_org(db, user)

    token = create_token(user.id)
    orgs = _user_orgs(user.id, db)
    org_id = orgs[0]["id"] if orgs else None
    if org_id:
        audit_log(db, org_id, user, "login", detail=f"Login from {ip}", request=request)
    return Token(
        access_token=token, token_type="bearer",
        user=UserOut.model_validate(user),
        orgs=orgs,
        active_org_id=org_id,
    )


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
    from ..seed_org import ensure_user_org
    ensure_user_org(db, user)
    token = create_token(user.id)
    orgs = _user_orgs(user.id, db)
    return Token(
        access_token=token, token_type="bearer",
        user=UserOut.model_validate(user),
        orgs=orgs,
        active_org_id=orgs[0]["id"] if orgs else None,
    )


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


# ── Password Reset ────────────────────────────────────────────────────────────

@router.post("/forgot-password")
def forgot_password(body: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    """Send a password-reset email. Always returns 200 to avoid user enumeration."""
    email = (body.get("email") or "").strip().lower()
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    user = db.query(User).filter(User.email == email, User.is_active == True).first()
    if user:
        # Invalidate old tokens
        db.query(PasswordResetToken).filter(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used == False
        ).update({"used": True})
        db.commit()
        token = secrets.token_urlsafe(32)
        db.add(PasswordResetToken(
            user_id=user.id, token=token,
            expires_at=datetime.utcnow() + timedelta(hours=1)
        ))
        db.commit()
        from ..services.email import send_password_reset
        background_tasks.add_task(send_password_reset, user.email, token)
    return {"message": "If that email is registered, a reset link has been sent."}


@router.post("/reset-password")
def reset_password(body: dict, db: Session = Depends(get_db)):
    token_str = (body.get("token") or "").strip()
    new_pw    = (body.get("password") or "").strip()
    if not token_str or not new_pw:
        raise HTTPException(status_code=400, detail="token and password required")
    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    rec = db.query(PasswordResetToken).filter(
        PasswordResetToken.token == token_str,
        PasswordResetToken.used == False
    ).first()
    if not rec or rec.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired reset link")
    rec.used = True
    user = rec.user
    user.hashed_password = pwd_context.hash(new_pw)
    db.commit()
    orgs = _user_orgs(user.id, db)
    if orgs:
        audit_log(db, orgs[0]["id"], user, "password_reset", entity_type="user", entity_id=user.id, detail=f"Password reset via email link for {user.username}")
    return {"message": "Password reset successfully. You can now sign in."}


# ── Self-serve Signup ─────────────────────────────────────────────────────────

@router.post("/signup", response_model=Token)
def signup(body: dict, background_tasks: BackgroundTasks, request: Request = None, db: Session = Depends(get_db)):
    _check_register_rate(request)
    """Create a new organisation + owner account in one step."""
    from ..seed_org import ensure_user_org
    username = (body.get("username") or "").strip()
    email    = (body.get("email") or "").strip().lower()
    password = (body.get("password") or "").strip()
    org_name = (body.get("org_name") or "").strip()

    if not all([username, email, password, org_name]):
        raise HTTPException(status_code=400, detail="username, email, password and org_name are required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    import re
    slug_base = re.sub(r"[^a-z0-9]+", "-", org_name.lower()).strip("-")[:40]
    slug = slug_base
    suffix = 1
    while db.query(Organization).filter(Organization.slug == slug).first():
        slug = f"{slug_base}-{suffix}"; suffix += 1

    org = Organization(name=org_name, slug=slug, plan="starter")
    db.add(org); db.flush()

    user = User(username=username, email=email,
                hashed_password=pwd_context.hash(password), is_active=True)
    db.add(user); db.flush()

    db.add(OrganizationMember(org_id=org.id, user_id=user.id, role="owner"))
    db.commit(); db.refresh(user)

    audit_log(db, org.id, user, "signup", entity_type="user", entity_id=user.id,
              detail=f"New org '{org_name}' created by '{username}'")

    from ..services.email import send_welcome
    background_tasks.add_task(send_welcome, email, username, org_name)

    token = create_token(user.id)
    orgs  = _user_orgs(user.id, db)
    return Token(access_token=token, token_type="bearer",
                 user=UserOut.model_validate(user),
                 orgs=orgs, active_org_id=orgs[0]["id"] if orgs else None)


# ── Invitation accept ─────────────────────────────────────────────────────────

@router.get("/invite/{token}")
def get_invite_info(token: str, db: Session = Depends(get_db)):
    """Return invite metadata so the frontend can pre-fill the accept form."""
    inv = db.query(OrgInvitation).filter(
        OrgInvitation.token == token,
        OrgInvitation.accepted_at == None
    ).first()
    if not inv or inv.expires_at < datetime.utcnow():
        raise HTTPException(status_code=404, detail="Invitation not found or expired")
    return {"org_name": inv.organization.name, "email": inv.email, "role": inv.role}


@router.post("/accept-invite", response_model=Token)
def accept_invite(body: dict, request: Request = None, db: Session = Depends(get_db)):
    _check_register_rate(request)
    """Accept an email invitation — creates account if needed, adds to org."""
    token_str = (body.get("token") or "").strip()
    username  = (body.get("username") or "").strip()
    password  = (body.get("password") or "").strip()
    if not all([token_str, username, password]):
        raise HTTPException(status_code=400, detail="token, username and password required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")

    inv = db.query(OrgInvitation).filter(
        OrgInvitation.token == token_str,
        OrgInvitation.accepted_at == None
    ).first()
    if not inv or inv.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="Invalid or expired invitation")

    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")

    user = db.query(User).filter(User.email == inv.email).first()
    if not user:
        user = User(username=username, email=inv.email,
                    hashed_password=pwd_context.hash(password), is_active=True)
        db.add(user); db.flush()
    else:
        user.hashed_password = pwd_context.hash(password)

    existing = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == inv.org_id,
        OrganizationMember.user_id == user.id
    ).first()
    if existing:
        existing.is_active = True; existing.role = inv.role
    else:
        db.add(OrganizationMember(org_id=inv.org_id, user_id=user.id,
                                  role=inv.role, invited_by=inv.invited_by))
    inv.accepted_at = datetime.utcnow()
    db.commit(); db.refresh(user)

    audit_log(db, inv.org_id, user, "accept_invite", entity_type="user", entity_id=user.id,
              detail=f"'{username}' accepted invitation to org #{inv.org_id} as {inv.role}")

    token = create_token(user.id)
    orgs  = _user_orgs(user.id, db)
    return Token(access_token=token, token_type="bearer",
                 user=UserOut.model_validate(user),
                 orgs=orgs, active_org_id=orgs[0]["id"] if orgs else None)
