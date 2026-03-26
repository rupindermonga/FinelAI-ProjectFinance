from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from ..database import get_db
from ..models import ColumnConfig, User
from ..schemas import ColumnConfigCreate, ColumnConfigUpdate, ColumnConfigOut
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/columns", tags=["columns"])


@router.get("", response_model=List[ColumnConfigOut])
def list_columns(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return (
        db.query(ColumnConfig)
        .filter(ColumnConfig.user_id == current_user.id)
        .order_by(ColumnConfig.display_order)
        .all()
    )


@router.post("", response_model=ColumnConfigOut)
def create_column(
    body: ColumnConfigCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    # Prevent duplicate field keys for same user
    existing = db.query(ColumnConfig).filter(
        ColumnConfig.user_id == current_user.id,
        ColumnConfig.field_key == body.field_key
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Field key '{body.field_key}' already exists")

    col = ColumnConfig(
        user_id=current_user.id,
        field_key=body.field_key,
        field_label=body.field_label,
        field_description=body.field_description,
        field_type=body.field_type,
        display_order=body.display_order,
        is_system=False,
        is_active=True,
    )
    db.add(col)
    db.commit()
    db.refresh(col)
    return col


@router.put("/{col_id}", response_model=ColumnConfigOut)
def update_column(
    col_id: int,
    body: ColumnConfigUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    col = db.query(ColumnConfig).filter(
        ColumnConfig.id == col_id,
        ColumnConfig.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")

    _ALLOWED = {"field_label", "field_description", "field_type", "is_active", "is_exportable", "display_order"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in _ALLOWED:
            setattr(col, field, value)

    db.commit()
    db.refresh(col)
    return col


@router.delete("/{col_id}")
def delete_column(
    col_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    col = db.query(ColumnConfig).filter(
        ColumnConfig.id == col_id,
        ColumnConfig.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")
    if col.is_system:
        raise HTTPException(status_code=400, detail="System columns cannot be deleted. You can disable them instead.")

    db.delete(col)
    db.commit()
    return {"message": "Column deleted"}


@router.put("/{col_id}/toggle")
def toggle_column(
    col_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    col = db.query(ColumnConfig).filter(
        ColumnConfig.id == col_id,
        ColumnConfig.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")

    col.is_active = not col.is_active
    db.commit()
    db.refresh(col)
    return {"id": col.id, "is_active": col.is_active}


@router.put("/{col_id}/toggle-export")
def toggle_export(
    col_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    col = db.query(ColumnConfig).filter(
        ColumnConfig.id == col_id,
        ColumnConfig.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")

    col.is_exportable = not col.is_exportable
    db.commit()
    db.refresh(col)
    return {"id": col.id, "is_exportable": col.is_exportable}


@router.put("/{col_id}/toggle-view")
def toggle_view(
    col_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    col = db.query(ColumnConfig).filter(
        ColumnConfig.id == col_id,
        ColumnConfig.user_id == current_user.id
    ).first()
    if not col:
        raise HTTPException(status_code=404, detail="Column not found")

    col.is_viewable = not col.is_viewable
    db.commit()
    db.refresh(col)
    return {"id": col.id, "is_viewable": col.is_viewable}
