import os
import shutil
import uuid
import logging
from pathlib import Path
from typing import List
from datetime import datetime
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from ..models import Invoice, ColumnConfig, CategoryConfig, GeminiApiKey
from .gemini import extract_invoice_from_file


UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", "./uploads")


def save_upload_file(file_content: bytes, original_filename: str) -> str:
    """Save uploaded file to disk, return saved path."""
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    ext = Path(original_filename).suffix.lower()
    unique_name = f"{uuid.uuid4().hex}{ext}"
    dest_path = os.path.join(UPLOAD_FOLDER, unique_name)
    with open(dest_path, "wb") as f:
        f.write(file_content)
    return dest_path


def get_active_columns(db: Session, user_id: int) -> List[ColumnConfig]:
    return (
        db.query(ColumnConfig)
        .filter(ColumnConfig.user_id == user_id, ColumnConfig.is_active == True)
        .order_by(ColumnConfig.display_order)
        .all()
    )


def get_active_categories(db: Session, user_id: int) -> List[CategoryConfig]:
    return (
        db.query(CategoryConfig)
        .filter(CategoryConfig.user_id == user_id, CategoryConfig.is_active == True)
        .order_by(CategoryConfig.level, CategoryConfig.display_order)
        .all()
    )


async def process_invoice_file(
    invoice_id: int,
    file_path: str,
    user_id: int,
    db: Session,
    processing_store: dict
) -> None:
    """
    Background task: run Gemini extraction on one file, update DB record.
    processing_store is an in-memory dict shared across requests for SSE updates.
    """
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        return

    # Mark as processing
    invoice.status = "processing"
    db.commit()
    processing_store[invoice_id] = {"user_id": user_id, "status": "processing", "filename": invoice.original_filename}

    try:
        columns = get_active_columns(db, user_id)
        cats = get_active_categories(db, user_id)
        # Load active DB keys in priority order; .env key is appended as fallback inside gemini.py
        db_keys = [
            k.key_value for k in
            db.query(GeminiApiKey)
              .filter(GeminiApiKey.is_active == True)
              .order_by(GeminiApiKey.priority, GeminiApiKey.id)
              .all()
        ]
        data = await extract_invoice_from_file(file_path, columns, cats, db_keys)

        # Populate indexed fields from extracted data
        invoice.invoice_number = _str(data.get("invoice_number"))
        invoice.invoice_date = _str(data.get("invoice_date"))
        invoice.due_date = _str(data.get("due_date"))
        invoice.vendor_name = _str(data.get("vendor_name"))
        invoice.currency = _str(data.get("currency"))
        invoice.total_due = _num(data.get("total_due"))
        invoice.confidence_score = _num(data.get("confidence_score"))
        invoice.extracted_data = data
        invoice.status = "processed"
        invoice.processed_at = datetime.utcnow()

        processing_store[invoice_id] = {
            "user_id": user_id,
            "status": "processed",
            "filename": invoice.original_filename,
            "invoice_number": invoice.invoice_number,
            "vendor_name": invoice.vendor_name,
            "total_due": invoice.total_due,
            "currency": invoice.currency,
        }

    except Exception as e:
        logger.exception("Invoice %s processing failed: %s", invoice_id, e)
        invoice.status = "error"
        invoice.error_message = "Processing failed. Check server logs for details."
        processing_store[invoice_id] = {
            "user_id": user_id,
            "status": "error",
            "filename": invoice.original_filename,
            "error": "Processing failed",
        }

    db.commit()


def _str(val) -> str | None:
    if val is None:
        return None
    return str(val).strip() or None


def _num(val) -> float | None:
    if val is None:
        return None
    try:
        return float(val)
    except (TypeError, ValueError):
        return None
