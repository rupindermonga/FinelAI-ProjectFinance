import asyncio
import json
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from math import ceil

from ..database import get_db
from ..models import Invoice, User
from ..schemas import InvoiceOut, InvoiceListResponse
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/invoices", tags=["invoices"])

# In-memory processing status store (invoice_id -> status dict)
processing_store: dict = {}


def _apply_filters(query, user_id, start_date, end_date, vendor, currency, status_filter):
    query = query.filter(Invoice.user_id == user_id)
    if start_date:
        query = query.filter(Invoice.invoice_date >= start_date)
    if end_date:
        query = query.filter(Invoice.invoice_date <= end_date)
    if vendor:
        query = query.filter(Invoice.vendor_name.ilike(f"%{vendor}%"))
    if currency:
        query = query.filter(Invoice.currency == currency.upper())
    if status_filter:
        query = query.filter(Invoice.status == status_filter)
    return query


@router.get("", response_model=InvoiceListResponse)
def list_invoices(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    vendor: Optional[str] = None,
    currency: Optional[str] = None,
    status: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    query = db.query(Invoice)
    query = _apply_filters(query, current_user.id, start_date, end_date, vendor, currency, status)
    total = query.count()
    items = query.order_by(Invoice.processed_at.desc()).offset((page - 1) * limit).limit(limit).all()
    return InvoiceListResponse(
        items=items,
        total=total,
        page=page,
        limit=limit,
        pages=ceil(total / limit) if total else 0
    )


@router.get("/stats")
def get_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    base = db.query(Invoice).filter(Invoice.user_id == current_user.id)
    return {
        "total": base.count(),
        "processed": base.filter(Invoice.status == "processed").count(),
        "pending": base.filter(Invoice.status.in_(["pending", "processing"])).count(),
        "errors": base.filter(Invoice.status == "error").count(),
    }


@router.get("/stream")
async def stream_processing(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """SSE endpoint — auth via ?token= query param (EventSource doesn't support headers)."""
    from ..dependencies import SECRET_KEY, ALGORITHM
    from jose import jwt, JWTError
    from ..models import User as UserModel
    try:
        payload = jwt.decode(token or "", SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        current_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not current_user:
            raise ValueError("user not found")
    except Exception:
        from fastapi.responses import Response
        return Response(status_code=401)
    """SSE endpoint — streams live processing updates to client."""
    async def event_generator():
        seen = set()
        timeout = 120  # seconds
        elapsed = 0
        while elapsed < timeout:
            updates = []
            for inv_id, info in list(processing_store.items()):
                key = f"{inv_id}:{info['status']}"
                if key not in seen:
                    seen.add(key)
                    updates.append({"id": inv_id, **info})

            if updates:
                yield f"data: {json.dumps(updates)}\n\n"

            await asyncio.sleep(1)
            elapsed += 1

        yield "data: {\"done\": true}\n\n"

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@router.get("/{invoice_id}", response_model=InvoiceOut)
def get_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inv = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.user_id == current_user.id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return inv


@router.delete("/{invoice_id}")
def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inv = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.user_id == current_user.id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    db.delete(inv)
    db.commit()
    return {"message": "Invoice deleted"}
