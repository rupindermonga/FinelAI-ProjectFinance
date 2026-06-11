"""Sync invoices/transactions from Finel Books (books.finel.ai) into this app.

The books.finel.ai backend runs on the same VPS and its SQLite DB is readable
directly. Set BOOKS_DB_PATH=/opt/bookkeeping/app/bookkeeping.db in the env.
If BOOKS_DB_PATH is not set or the file doesn't exist, all endpoints return
a helpful 503 so the feature is cleanly disabled in dev/CI.
"""
import os
import sqlite3
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Invoice, User
from ..dependencies import get_current_user, get_current_org
from .audit import log as audit_log

router = APIRouter(prefix="/api/books", tags=["books-sync"])


def _books_db_path():
    return os.getenv("BOOKS_DB_PATH", "")


def _get_books_conn():
    path = _books_db_path()
    if not path or not os.path.exists(path):
        raise HTTPException(
            status_code=503,
            detail="Books integration not configured — set BOOKS_DB_PATH on the server.",
        )
    try:
        conn = sqlite3.connect(path, timeout=5, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Cannot open Books DB: {e}")


@router.get("/clients")
def list_books_clients(
    current_user: User = Depends(get_current_user),
    org_ctx=Depends(get_current_org),
):
    """Return all clients in the Books DB (for optional client filter)."""
    org, _ = org_ctx
    conn = _get_books_conn()
    try:
        rows = conn.execute(
            "SELECT id, business_name, base_currency FROM clients WHERE active=1 ORDER BY business_name"
        ).fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


@router.get("/preview")
def preview_books_transactions(
    client_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None, description="Filter by status e.g. approved"),
    limit: int = Query(200, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx=Depends(get_current_org),
):
    """
    Return transactions from Books that have not yet been imported.
    Excludes any transaction whose books_tx_id is already tracked in our invoices.
    """
    org, _ = org_ctx
    conn = _get_books_conn()
    try:
        # Transactions already imported (tracked via source_file = "books:<id>")
        imported = set(
            r[0]
            for r in db.execute(
                text(
                    "SELECT source_file FROM invoices "
                    "WHERE source='books' AND source_file IS NOT NULL AND org_id=:oid"
                ),
                {"oid": org.id},
            ).fetchall()
            if r[0]
        )

        where_parts = []
        params: dict = {}

        if client_id:
            where_parts.append("client_id = :cid")
            params["cid"] = client_id
        if status:
            where_parts.append("status = :status")
            params["status"] = status

        where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""
        rows = conn.execute(
            f"""
            SELECT id, client_id, vendor, date, total, subtotal, tax,
                   currency, category, gl_code, status, approval_status,
                   submitted_source, filename, created_at
            FROM transactions
            {where_clause}
            ORDER BY date DESC, created_at DESC
            LIMIT :lim
            """,
            {**params, "lim": limit},
        ).fetchall()

        result = []
        for r in rows:
            tx_id = f"books:{r['id']}"
            result.append(
                {
                    "id": r["id"],
                    "already_imported": tx_id in imported,
                    "vendor": r["vendor"] or "",
                    "date": r["date"] or "",
                    "total": r["total"],
                    "subtotal": r["subtotal"],
                    "tax": r["tax"],
                    "currency": r["currency"] or "CAD",
                    "category": r["category"] or "",
                    "gl_code": r["gl_code"] or "",
                    "status": r["status"] or "",
                    "approval_status": r["approval_status"] or "",
                    "filename": r["filename"] or "",
                    "source": r["submitted_source"] or "",
                    "created_at": r["created_at"] or "",
                }
            )
        return result
    finally:
        conn.close()


@router.post("/import")
def import_books_transactions(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    org_ctx=Depends(get_current_org),
):
    """
    Import selected Books transactions as invoices in this org.
    Body: { "transaction_ids": ["<uuid>", ...] }
    """
    org, _ = org_ctx
    tx_ids: list = body.get("transaction_ids", [])
    if not tx_ids:
        raise HTTPException(status_code=400, detail="No transaction_ids provided")
    if len(tx_ids) > 200:
        raise HTTPException(status_code=400, detail="Max 200 transactions per import")

    conn = _get_books_conn()
    try:
        placeholders = ",".join(["?" for _ in tx_ids])
        rows = conn.execute(
            f"""
            SELECT id, vendor, date, total, subtotal, tax, currency,
                   category, gl_code, status, filename, submitted_source, client_id
            FROM transactions
            WHERE id IN ({placeholders})
            """,
            tx_ids,
        ).fetchall()
    finally:
        conn.close()

    if not rows:
        raise HTTPException(status_code=404, detail="No matching transactions found in Books")

    # De-duplicate: skip any already imported
    already = set(
        r[0]
        for r in db.execute(
            text(
                "SELECT source_file FROM invoices "
                "WHERE source='books' AND source_file IS NOT NULL AND org_id=:oid"
            ),
            {"oid": org.id},
        ).fetchall()
        if r[0]
    )

    created = []
    skipped = []
    for r in rows:
        source_key = f"books:{r['id']}"
        if source_key in already:
            skipped.append(r["id"])
            continue

        inv = Invoice(
            user_id=current_user.id,
            org_id=org.id,
            source="books",
            source_file=source_key,
            original_filename=r["filename"] or "",
            status="processed",
            invoice_date=r["date"] or "",
            vendor_name=r["vendor"] or "",
            currency=r["currency"] or "CAD",
            total_due=float(r["total"] or 0),
            processed_at=datetime.utcnow(),
            extracted_data={
                "vendor_name": r["vendor"] or "",
                "invoice_date": r["date"] or "",
                "total_due": r["total"],
                "subtotal": r["subtotal"],
                "tax": r["tax"],
                "currency": r["currency"] or "CAD",
                "category": r["category"] or "",
                "gl_code": r["gl_code"] or "",
                "books_status": r["status"] or "",
                "books_source": r["submitted_source"] or "",
            },
        )
        db.add(inv)
        db.flush()
        created.append(inv.id)

    db.commit()
    audit_log(
        db, current_user, "books_sync", "import",
        f"Imported {len(created)} transactions from Books (skipped {len(skipped)} duplicates)",
        org_id=org.id,
    )
    return {
        "imported": len(created),
        "skipped": len(skipped),
        "invoice_ids": created,
    }
