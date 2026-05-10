"""Admin-only routes: manage Gemini API keys and user accounts."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from passlib.context import CryptContext
from typing import List

from ..database import get_db
from ..models import GeminiApiKey, User, OrganizationMember
from ..schemas import ApiKeyCreate, ApiKeyUpdate, ApiKeyOut, UserOut
from ..dependencies import get_current_user
from .audit import log as audit_log

def _admin_org_id(admin: User, db) -> int | None:
    m = db.query(OrganizationMember).filter(OrganizationMember.user_id == admin.id, OrganizationMember.is_active == True).first()
    return m.org_id if m else None

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _require_admin(current_user: User = Depends(get_current_user)) -> User:
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


def _mask(key_value: str) -> str:
    """Return a masked preview of the API key."""
    if len(key_value) > 12:
        return key_value[:8] + "..." + key_value[-4:]
    return "****"


def _to_out(k: GeminiApiKey) -> ApiKeyOut:
    return ApiKeyOut(
        id=k.id,
        label=k.label,
        key_preview=_mask(k.key_value),
        priority=k.priority,
        is_active=k.is_active,
        created_at=k.created_at,
    )


@router.get("/api-keys", response_model=List[ApiKeyOut])
def list_api_keys(
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    keys = db.query(GeminiApiKey).order_by(GeminiApiKey.priority, GeminiApiKey.id).all()
    return [_to_out(k) for k in keys]


@router.post("/api-keys", response_model=ApiKeyOut)
def create_api_key(
    body: ApiKeyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    if not body.label.strip():
        raise HTTPException(status_code=400, detail="label cannot be empty")
    if not body.key_value.strip():
        raise HTTPException(status_code=400, detail="key_value cannot be empty")

    key = GeminiApiKey(
        label=body.label.strip(),
        key_value=body.key_value.strip(),
        priority=body.priority,
        is_active=body.is_active,
    )
    db.add(key)
    db.commit()
    db.refresh(key)
    return _to_out(key)


@router.put("/api-keys/{key_id}", response_model=ApiKeyOut)
def update_api_key(
    key_id: int,
    body: ApiKeyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    key = db.query(GeminiApiKey).filter(GeminiApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    _ALLOWED = {"label", "priority", "is_active"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in _ALLOWED:
            setattr(key, field, value)
    db.commit()
    db.refresh(key)
    return _to_out(key)


@router.delete("/api-keys/{key_id}")
def delete_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    key = db.query(GeminiApiKey).filter(GeminiApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    db.delete(key)
    db.commit()
    return {"message": f"Deleted '{key.label}'"}


@router.put("/api-keys/{key_id}/toggle")
def toggle_api_key(
    key_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(_require_admin),
):
    key = db.query(GeminiApiKey).filter(GeminiApiKey.id == key_id).first()
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    key.is_active = not key.is_active
    db.commit()
    return {"id": key.id, "is_active": key.is_active}


# ─── User Management ────────────────────────────────────────────────────────

@router.get("/users")
def list_users(db: Session = Depends(get_db), admin: User = Depends(_require_admin)):
    users = db.query(User).order_by(User.created_at.desc()).all()
    return [{"id": u.id, "username": u.username, "email": u.email, "is_active": u.is_active, "is_admin": u.is_admin, "created_at": u.created_at.isoformat() if u.created_at else None} for u in users]


@router.post("/users")
def create_user(body: dict, db: Session = Depends(get_db), admin: User = Depends(_require_admin)):
    username = (body.get("username") or "").strip()
    email = (body.get("email") or "").strip()
    password = body.get("password", "")
    if len(username) < 3:
        raise HTTPException(status_code=400, detail="Username must be at least 3 characters")
    if not email or "@" not in email:
        raise HTTPException(status_code=400, detail="Valid email required")
    if len(password) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(status_code=400, detail="Username already taken")
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        username=username,
        email=email,
        hashed_password=pwd_context.hash(password),
        is_admin=body.get("is_admin", False),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Seed default columns and project for new user
    from ..seed_columns import seed_default_columns
    seed_default_columns(db, user.id)
    from ..seed_project import seed_project_finance
    seed_project_finance(db, user.id)

    org_id = _admin_org_id(admin, db)
    if org_id:
        audit_log(db, org_id, admin, "create_user", entity_type="user",
                  entity_id=user.id, detail=f"Admin created user '{username}' (is_admin={user.is_admin})")
    return {"id": user.id, "username": user.username, "email": user.email, "is_active": user.is_active, "is_admin": user.is_admin}


@router.put("/users/{user_id}/toggle-active")
def toggle_user_active(user_id: int, db: Session = Depends(get_db), admin: User = Depends(_require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot deactivate yourself")
    user.is_active = not user.is_active
    db.commit()
    return {"id": user.id, "is_active": user.is_active}


@router.put("/users/{user_id}/reset-password")
def reset_password(user_id: int, body: dict, db: Session = Depends(get_db), admin: User = Depends(_require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    new_pw = body.get("password", "")
    if len(new_pw) < 8:
        raise HTTPException(status_code=400, detail="Password must be at least 8 characters")
    user.hashed_password = pwd_context.hash(new_pw)
    db.commit()
    return {"message": f"Password reset for {user.username}"}


@router.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db), admin: User = Depends(_require_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="Cannot delete yourself")
    if user.is_admin:
        raise HTTPException(status_code=400, detail="Cannot delete another admin")
    uname = user.username
    org_id = _admin_org_id(admin, db)
    db.delete(user)
    db.commit()
    if org_id:
        audit_log(db, org_id, admin, "delete_user", entity_type="user",
                  entity_id=user_id, detail=f"Admin deleted user '{uname}'")
    return {"message": f"User {uname} deleted"}
