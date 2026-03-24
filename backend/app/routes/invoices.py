import asyncio
import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from math import ceil
import aiofiles
from dotenv import load_dotenv

from ..database import get_db
from ..models import Invoice, User, Correction
from ..dependencies import get_current_user
from ..schemas import InvoiceOut, InvoiceListResponse
from ..dependencies import get_current_user

load_dotenv()
_UPLOAD_DIR = os.path.abspath(os.getenv("UPLOAD_FOLDER", "./uploads"))

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


@router.post("/sse-token")
def create_sse_token(current_user: User = Depends(get_current_user)):
    """Issue a short-lived (60s) token for SSE — minimizes URL leakage window."""
    from ..dependencies import SECRET_KEY, ALGORITHM
    from jose import jwt as _jwt
    expire = datetime.utcnow() + timedelta(seconds=60)
    sse_token = _jwt.encode({"sub": str(current_user.id), "exp": expire, "scope": "sse"}, SECRET_KEY, algorithm=ALGORITHM)
    return {"sse_token": sse_token}


@router.get("/stream")
async def stream_processing(
    token: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    """SSE endpoint — auth via ?token= query param with SHORT-LIVED SSE token.

    SECURITY NOTE: EventSource API does not support custom headers, so a token
    must be passed as a query parameter.  Mitigations:
      • SSE tokens expire in 60 seconds (not the main session JWT).
      • SSE tokens have scope=sse and cannot be used for other endpoints.
      • SSE is only used during active upload processing (short-lived connection).
    """
    from ..dependencies import SECRET_KEY, ALGORITHM
    from jose import jwt, JWTError
    from ..models import User as UserModel
    try:
        payload = jwt.decode(token or "", SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        current_user = db.query(UserModel).filter(UserModel.id == user_id).first()
        if not current_user or not current_user.is_active:
            raise ValueError("user not found or disabled")
    except Exception:
        from fastapi.responses import Response
        return Response(status_code=401)
    """SSE endpoint — streams live processing updates to client."""
    async def event_generator():
        seen = set()
        idle_timeout = 30   # close after 30s of no new events
        max_timeout = 300   # hard cap at 5 minutes
        idle = 0
        total = 0
        while idle < idle_timeout and total < max_timeout:
            updates = []
            for inv_id, info in list(processing_store.items()):
                # Only stream events owned by the authenticated user
                if info.get("user_id") != current_user.id:
                    continue
                key = f"{inv_id}:{info['status']}"
                if key not in seen:
                    seen.add(key)
                    # Strip internal user_id before sending to client
                    updates.append({"id": inv_id, **{k: v for k, v in info.items() if k != "user_id"}})

            if updates:
                yield f"data: {json.dumps(updates)}\n\n"
                idle = 0  # reset idle timer on activity
            else:
                idle += 1

            await asyncio.sleep(1)
            total += 1

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


# Indexed fields that live as columns on the Invoice table (not just in extracted_data JSON)
_INDEXED_FIELDS = {"invoice_number", "invoice_date", "due_date", "vendor_name", "currency", "total_due", "billed_to", "billing_type", "vendor_on_record"}


@router.patch("/{invoice_id}")
def update_invoice_fields(
    invoice_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Update extracted fields on a processed invoice.
    Body: { "field_key": "new_value", ... }
    Saves corrections to the corrections table so Gemini can learn from them.
    """
    inv = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.user_id == current_user.id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")

    data = dict(inv.extracted_data or {})
    for field_key, new_value in body.items():
        old_value = data.get(field_key)

        # Save correction if value actually changed
        if str(old_value) != str(new_value):
            correction = Correction(
                user_id=current_user.id,
                field_key=field_key,
                original_value=str(old_value) if old_value is not None else None,
                corrected_value=str(new_value) if new_value is not None else "",
                vendor_name=inv.vendor_name,
            )
            db.add(correction)

        # Update extracted_data JSON
        data[field_key] = new_value

        # Also update indexed column if applicable
        if field_key in _INDEXED_FIELDS:
            if field_key == "total_due":
                try:
                    setattr(inv, field_key, float(new_value) if new_value else None)
                except (TypeError, ValueError):
                    pass
            else:
                setattr(inv, field_key, str(new_value) if new_value else None)

    inv.extracted_data = data

    # Recalculate allocation amounts if total_due changed
    if "total_due" in body and inv.allocations:
        new_total = inv.total_due or 0.0
        for alloc in inv.allocations:
            alloc.amount = round(new_total * alloc.percentage / 100.0, 2)

    db.commit()
    db.refresh(inv)
    return {"message": "Updated", "id": inv.id}


_FILE_MIME = {
    ".pdf":  "application/pdf",
    ".jpg":  "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png":  "image/png",
    ".tiff": "image/tiff",
    ".tif":  "image/tiff",
    ".webp": "image/webp",
}


@router.get("/{invoice_id}/file")
async def get_invoice_file(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Stream the original uploaded file so the browser can preview it inline."""
    inv = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.user_id == current_user.id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if not inv.source_file or not os.path.isfile(inv.source_file):
        raise HTTPException(status_code=404, detail="Source file not available on disk")

    # Path traversal guard: ensure file is inside the upload directory
    safe_path = os.path.abspath(inv.source_file)
    try:
        Path(safe_path).relative_to(Path(_UPLOAD_DIR))
    except ValueError:
        raise HTTPException(status_code=403, detail="Access denied")

    ext = Path(safe_path).suffix.lower()
    media_type = _FILE_MIME.get(ext, "application/octet-stream")
    filename = inv.original_filename or os.path.basename(inv.source_file)

    async def _streamer():
        async with aiofiles.open(safe_path, "rb") as f:
            while True:
                chunk = await f.read(65536)
                if not chunk:
                    break
                yield chunk

    return StreamingResponse(
        _streamer(),
        media_type=media_type,
        headers={"Content-Disposition": f'inline; filename="{filename}"'},
    )


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

    # Delete DB record first so a failed commit doesn't orphan the record
    file_to_delete = inv.source_file
    db.delete(inv)
    db.commit()

    # Now safe to remove the backing file
    if file_to_delete and os.path.isfile(file_to_delete):
        try:
            os.remove(file_to_delete)
        except OSError:
            pass  # File already gone or no permission — DB record is already removed

    return {"message": "Invoice deleted"}
