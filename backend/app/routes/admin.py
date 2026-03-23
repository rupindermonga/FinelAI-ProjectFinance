"""Admin-only routes: manage the pool of Gemini API keys."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import GeminiApiKey, User
from ..schemas import ApiKeyCreate, ApiKeyUpdate, ApiKeyOut
from ..dependencies import get_current_user

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
