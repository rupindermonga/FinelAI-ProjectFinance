import asyncio
import json
import os
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_
from typing import Optional
from math import ceil
import aiofiles
from dotenv import load_dotenv

from ..database import get_db
from ..models import Invoice, User
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
    if not safe_path.startswith(_UPLOAD_DIR + os.sep) and safe_path != _UPLOAD_DIR:
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

    # Delete backing file from disk before removing the DB record
    if inv.source_file and os.path.isfile(inv.source_file):
        try:
            os.remove(inv.source_file)
        except OSError:
            pass  # File already gone or no permission — proceed with DB delete

    db.delete(inv)
    db.commit()
    return {"message": "Invoice deleted"}
