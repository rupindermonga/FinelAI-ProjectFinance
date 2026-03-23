import asyncio
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
from pathlib import Path

from ..database import get_db
from ..models import Invoice, User
from ..dependencies import get_current_user
from ..services.extractor import save_upload_file, process_invoice_file
from ..services.gemini import check_api_key
from .invoices import processing_store

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".tiff", ".tif", ".webp"}


@router.post("")
async def upload_invoices(
    background_tasks: BackgroundTasks,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not check_api_key(db):
        raise HTTPException(
            status_code=400,
            detail="No Gemini API key configured. Add one in Admin → Settings → API Keys, or set GEMINI_API_KEY in .env."
        )

    results = []
    for upload in files:
        ext = Path(upload.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            results.append({
                "filename": upload.filename,
                "status": "rejected",
                "reason": f"Unsupported file type '{ext}'. Allowed: PDF, JPG, PNG, TIFF, WEBP"
            })
            continue

        _MAX = 50 * 1024 * 1024  # 50 MB
        # Reject early using Content-Length header when browser provides it
        cl = upload.headers.get("content-length")
        if cl and int(cl) > _MAX:
            results.append({
                "filename": upload.filename,
                "status": "rejected",
                "reason": "File too large (max 50 MB)"
            })
            continue
        # Read in chunks; abort if accumulated size exceeds limit
        chunks = []
        total = 0
        oversized = False
        while True:
            chunk = await upload.read(65536)
            if not chunk:
                break
            total += len(chunk)
            if total > _MAX:
                oversized = True
                break
            chunks.append(chunk)
        if oversized:
            results.append({
                "filename": upload.filename,
                "status": "rejected",
                "reason": "File too large (max 50 MB)"
            })
            continue
        content = b"".join(chunks)

        # Save file to disk
        saved_path = save_upload_file(content, upload.filename)

        # Create invoice record
        invoice = Invoice(
            user_id=current_user.id,
            source="upload",
            source_file=saved_path,
            original_filename=upload.filename,
            status="pending",
        )
        db.add(invoice)
        db.commit()
        db.refresh(invoice)

        # Queue background extraction
        background_tasks.add_task(
            process_invoice_file,
            invoice.id,
            saved_path,
            current_user.id,
            db,
            processing_store
        )

        results.append({
            "invoice_id": invoice.id,
            "filename": upload.filename,
            "status": "queued"
        })

    return {"uploaded": len(results), "results": results}


@router.get("/status/{invoice_id}")
def get_upload_status(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    inv = db.query(Invoice).filter(
        Invoice.id == invoice_id, Invoice.user_id == current_user.id
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return {
        "id": inv.id,
        "status": inv.status,
        "original_filename": inv.original_filename,
        "error_message": inv.error_message,
    }
