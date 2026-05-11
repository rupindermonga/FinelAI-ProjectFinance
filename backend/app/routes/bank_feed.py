"""
Bank Feed — Connect bank accounts, import transactions, and AI-powered reconciliation.

Supports:
- Flinks (Canadian open banking) — stores loginId from Flinks iframe
- Manual CSV import (RBC, TD, Scotiabank, BMO, etc.)
- Gemini AI batch-matching of transactions to invoices, vendors, and cost categories
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, FINANCE_WRITE_ROLES, FINANCE_READ_ROLES, call_gemini_api
from ..models import BankFeedConnection, BankFeedTransaction, User

router = APIRouter(prefix="/api/bank-feed", tags=["bank-feed"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── 1. List connections ──────────────────────────────────────────────────────

@router.get("/connections")
def list_connections(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all bank accounts connected for this org."""
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)

    connections = (
        db.query(BankFeedConnection)
        .filter(BankFeedConnection.org_id == current_user.org_id)
        .order_by(BankFeedConnection.created_at.desc())
        .all()
    )

    result = []
    for c in connections:
        # Count transactions per connection
        txn_count = (
            db.query(BankFeedTransaction)
            .filter(BankFeedTransaction.connection_id == c.id)
            .count()
        )
        unmatched_count = (
            db.query(BankFeedTransaction)
            .filter(
                BankFeedTransaction.connection_id == c.id,
                BankFeedTransaction.status == "unmatched",
            )
            .count()
        )
        result.append({
            "id": c.id,
            "provider": c.provider,
            "institution_name": c.institution_name,
            "account_name": c.account_name,
            "account_type": c.account_type,
            "masked_account": c.masked_account,
            "status": c.status,
            "last_synced_at": c.last_synced_at.isoformat() if c.last_synced_at else None,
            "balance": c.balance,
            "currency": c.currency,
            "notes": c.notes,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "transaction_count": txn_count,
            "unmatched_count": unmatched_count,
        })

    return {"connections": result, "total": len(result)}


# ─── 2. Create connection ─────────────────────────────────────────────────────

@router.post("/connections", status_code=201)
def create_connection(
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new bank account connection.

    For Flinks: pass flinks_login_id (returned from Flinks iframe) — status auto-set to 'active'.
    For manual: omit flinks_login_id — status starts as 'pending' until transactions are imported.

    Body fields: provider, institution_name, account_name, account_type,
                 masked_account, flinks_login_id, notes
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_WRITE_ROLES)

    provider = body.get("provider", "manual")
    flinks_login_id = body.get("flinks_login_id") or None

    # Determine initial status
    if flinks_login_id:
        initial_status = "active"
    else:
        initial_status = "pending"

    conn = BankFeedConnection(
        org_id=current_user.org_id,
        provider=provider,
        institution_name=body.get("institution_name"),
        account_name=body.get("account_name"),
        account_type=body.get("account_type"),
        masked_account=body.get("masked_account"),
        flinks_login_id=flinks_login_id,
        status=initial_status,
        currency=body.get("currency", "CAD"),
        notes=body.get("notes"),
        created_by=current_user.id,
    )
    db.add(conn)
    db.commit()
    db.refresh(conn)

    return {
        "msg": "Bank account connected successfully.",
        "id": conn.id,
        "status": conn.status,
        "provider": conn.provider,
    }


# ─── 3. Disconnect ────────────────────────────────────────────────────────────

@router.delete("/connections/{connection_id}")
def disconnect_connection(
    connection_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Disconnect a bank account (marks as disconnected; preserves transaction history)."""
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_WRITE_ROLES)

    conn = db.query(BankFeedConnection).filter(
        BankFeedConnection.id == connection_id,
        BankFeedConnection.org_id == current_user.org_id,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Bank connection not found")

    conn.status = "disconnected"
    db.commit()
    return {"msg": "Bank account disconnected. Transaction history preserved."}


# ─── 4. Sync / Import transactions ───────────────────────────────────────────

@router.post("/connections/{connection_id}/sync")
def sync_connection(
    connection_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Sync transactions for a bank connection.

    - Flinks connections (active + flinks_login_id set): returns a stub message directing
      to live sync activation (FLINKS_API_KEY required).
    - Manual connections: accepts body.transactions list and bulk-inserts.
      Each transaction: {date, description, amount, balance_after (optional)}
      Deduplication is performed on (date, description, amount).
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_WRITE_ROLES)

    conn = db.query(BankFeedConnection).filter(
        BankFeedConnection.id == connection_id,
        BankFeedConnection.org_id == current_user.org_id,
    ).first()
    if not conn:
        raise HTTPException(status_code=404, detail="Bank connection not found")

    # Flinks live sync stub
    if conn.provider == "flinks" and conn.status == "active" and conn.flinks_login_id:
        return {
            "msg": (
                "Flinks sync requires FLINKS_API_KEY — contact support to activate live sync"
            ),
            "manual_import_available": True,
        }

    # Manual import
    transactions = body.get("transactions", [])
    if not transactions:
        raise HTTPException(status_code=422, detail="No transactions provided. Pass 'transactions' array.")

    inserted = 0
    skipped = 0

    for txn in transactions:
        txn_date = str(txn.get("date", "")).strip()
        description = str(txn.get("description", "")).strip()
        try:
            amount = float(txn.get("amount", 0))
        except (ValueError, TypeError):
            skipped += 1
            continue

        if not txn_date or not description:
            skipped += 1
            continue

        # Deduplication: skip if same (date, description, amount) already exists for this connection
        existing = db.execute(
            text(
                "SELECT id FROM bank_feed_transactions "
                "WHERE connection_id=:cid AND transaction_date=:d AND description=:desc AND amount=:amt "
                "LIMIT 1"
            ),
            {"cid": connection_id, "d": txn_date, "desc": description, "amt": amount},
        ).fetchone()

        if existing:
            skipped += 1
            continue

        balance_after = txn.get("balance_after")
        if balance_after is not None:
            try:
                balance_after = float(balance_after)
            except (ValueError, TypeError):
                balance_after = None

        new_txn = BankFeedTransaction(
            connection_id=connection_id,
            org_id=current_user.org_id,
            transaction_date=txn_date,
            description=description,
            amount=amount,
            balance_after=balance_after,
            raw_description=description,
            transaction_type=txn.get("transaction_type"),
            reference_number=txn.get("reference_number"),
            status="unmatched",
        )
        db.add(new_txn)
        inserted += 1

    if inserted > 0:
        conn.last_synced_at = datetime.utcnow()
        # Update balance from last transaction if present
        if transactions and transactions[-1].get("balance_after") is not None:
            try:
                conn.balance = float(transactions[-1]["balance_after"])
            except (ValueError, TypeError):
                pass
        conn.status = "active"

    db.commit()

    return {
        "msg": f"Import complete. {inserted} transactions added, {skipped} skipped (duplicates or invalid).",
        "inserted": inserted,
        "skipped": skipped,
    }


# ─── 5. List transactions ─────────────────────────────────────────────────────

@router.get("/transactions")
def list_transactions(
    connection_id: Optional[int] = Query(None),
    status: Optional[str] = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List bank feed transactions for the org.
    Optional filters: connection_id, status (unmatched|ai_suggested|confirmed|excluded).
    Returns transactions with summary counts.
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)

    query = db.query(BankFeedTransaction).filter(
        BankFeedTransaction.org_id == current_user.org_id
    )

    if connection_id:
        query = query.filter(BankFeedTransaction.connection_id == connection_id)
    if status:
        query = query.filter(BankFeedTransaction.status == status)

    txns = query.order_by(BankFeedTransaction.transaction_date.desc()).limit(limit).all()

    # Summary counts for entire org (not filtered by limit)
    summary_query = db.query(BankFeedTransaction).filter(
        BankFeedTransaction.org_id == current_user.org_id
    )
    if connection_id:
        summary_query = summary_query.filter(BankFeedTransaction.connection_id == connection_id)

    all_txns = summary_query.all()
    status_counts = {"unmatched": 0, "ai_suggested": 0, "confirmed": 0, "excluded": 0}
    for t in all_txns:
        if t.status in status_counts:
            status_counts[t.status] += 1

    result = []
    for t in txns:
        result.append({
            "id": t.id,
            "connection_id": t.connection_id,
            "transaction_date": t.transaction_date,
            "description": t.description,
            "amount": t.amount,
            "balance_after": t.balance_after,
            "transaction_type": t.transaction_type,
            "reference_number": t.reference_number,
            "status": t.status,
            "ai_vendor_suggestion": t.ai_vendor_suggestion,
            "ai_category_suggestion": t.ai_category_suggestion,
            "ai_invoice_id": t.ai_invoice_id,
            "ai_confidence": t.ai_confidence,
            "ai_reasoning": t.ai_reasoning,
            "matched_invoice_id": t.matched_invoice_id,
            "matched_vendor_id": t.matched_vendor_id,
            "matched_category_id": t.matched_category_id,
            "notes": t.notes,
            "created_at": t.created_at.isoformat() if t.created_at else None,
        })

    return {
        "transactions": result,
        "returned": len(result),
        "summary": status_counts,
    }


# ─── 6. AI match all unmatched transactions ───────────────────────────────────

@router.post("/ai-match-all")
async def ai_match_all(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Batch-analyze all 'unmatched' transactions for this org using Gemini AI.

    Fetches unpaid invoices, vendor directory, and cost categories, then sends
    Gemini a structured prompt to suggest matches. Updates ai_* fields on each
    transaction and sets status to 'ai_suggested' where confidence >= low.

    Returns a summary of matches found.
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_WRITE_ROLES)

    org_id = current_user.org_id

    # ── Fetch data ────────────────────────────────────────────────────────────

    txns = db.execute(
        text(
            "SELECT id, transaction_date, description, amount "
            "FROM bank_feed_transactions "
            "WHERE org_id=:oid AND status='unmatched' "
            "LIMIT 200"
        ),
        {"oid": org_id},
    ).fetchall()

    if not txns:
        return {"matched": 0, "unmatched": 0, "total": 0, "msg": "No unmatched transactions found."}

    invoices = db.execute(
        text(
            "SELECT id, invoice_number, vendor_name, total_due, invoice_date "
            "FROM invoices "
            "WHERE org_id=:oid AND payment_status='unpaid' "
            "LIMIT 300"
        ),
        {"oid": org_id},
    ).fetchall()

    vendors = db.execute(
        text(
            "SELECT id, name FROM org_vendors "
            "WHERE org_id=:oid AND is_active=1 "
            "LIMIT 100"
        ),
        {"oid": org_id},
    ).fetchall()

    cats = db.execute(
        text(
            "SELECT id, name FROM cost_categories "
            "WHERE org_id=:oid "
            "LIMIT 50"
        ),
        {"oid": org_id},
    ).fetchall()

    # ── Build prompt ──────────────────────────────────────────────────────────

    txn_list = [
        {"id": row[0], "date": row[1], "description": row[2], "amount": row[3]}
        for row in txns
    ]
    invoice_list = [
        {"id": row[0], "invoice_number": row[1], "vendor_name": row[2],
         "amount": row[3], "invoice_date": row[4]}
        for row in invoices
    ]
    vendor_list = [{"id": row[0], "name": row[1]} for row in vendors]
    category_list = [{"id": row[0], "name": row[1]} for row in cats]

    prompt = f"""You are a Canadian construction finance reconciliation assistant.

Your task is to match bank transactions to unpaid invoices, vendors, and cost categories.

BANK TRANSACTIONS (need matching):
{json.dumps(txn_list, indent=2)}

UNPAID INVOICES:
{json.dumps(invoice_list, indent=2)}

VENDOR DIRECTORY:
{json.dumps(vendor_list, indent=2)}

COST CATEGORIES:
{json.dumps(category_list, indent=2)}

For each transaction, suggest the best match. Use the transaction description, amount, and date
to find matching invoices (amounts should be close). Look for vendor names embedded in descriptions.

Return ONLY a valid JSON array — no markdown fences, no explanation, just the raw array.
Each element must have exactly these keys:
  transaction_id, vendor_suggestion, vendor_id, category_suggestion, category_id,
  invoice_id, confidence, reasoning

Rules:
- confidence must be one of: "high", "medium", "low", "none"
- Set vendor_id / category_id / invoice_id to null if no match found
- Set confidence to "none" if the transaction is clearly unidentifiable (e.g., ATM, internal transfer)
- For amount matching: within 1% is high confidence; within 5% is medium; within 15% is low
- reasoning should be one short sentence explaining the match

Example element:
{{
  "transaction_id": 123,
  "vendor_suggestion": "Rona Inc",
  "vendor_id": 45,
  "category_suggestion": "Materials",
  "category_id": 12,
  "invoice_id": 78,
  "confidence": "high",
  "reasoning": "Transaction '$RONA LEASIDE' matches vendor 'Rona Inc', amount $2,847.50 matches unpaid invoice #INV-2024-089"
}}
"""

    # ── Call Gemini ───────────────────────────────────────────────────────────

    raw = await call_gemini_api(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.1, "maxOutputTokens": 8192},
        },
        timeout=90,
    )

    # ── Parse response ────────────────────────────────────────────────────────

    try:
        candidates = raw.get("candidates", [])
        if not candidates:
            raise ValueError("No candidates in Gemini response")
        text_content = candidates[0]["content"]["parts"][0]["text"].strip()

        # Strip markdown fences if present
        if text_content.startswith("```"):
            lines = text_content.splitlines()
            text_content = "\n".join(
                line for line in lines if not line.strip().startswith("```")
            )

        matches = json.loads(text_content)
        if not isinstance(matches, list):
            raise ValueError("Expected a JSON array from Gemini")
    except (KeyError, IndexError, json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=502,
            detail=f"Failed to parse Gemini response: {str(exc)}",
        )

    # ── Apply updates ─────────────────────────────────────────────────────────

    matched_count = 0
    unmatched_count = 0

    for match in matches:
        txn_id = match.get("transaction_id")
        if not txn_id:
            continue

        confidence = match.get("confidence", "none")

        txn_obj = db.query(BankFeedTransaction).filter(
            BankFeedTransaction.id == txn_id,
            BankFeedTransaction.org_id == org_id,
        ).first()
        if not txn_obj:
            continue

        txn_obj.ai_vendor_suggestion = match.get("vendor_suggestion")
        txn_obj.ai_category_suggestion = match.get("category_suggestion")
        txn_obj.ai_invoice_id = match.get("invoice_id")
        txn_obj.ai_confidence = confidence
        txn_obj.ai_reasoning = match.get("reasoning")

        if confidence in ("high", "medium", "low"):
            txn_obj.status = "ai_suggested"
            matched_count += 1
        else:
            unmatched_count += 1

    db.commit()

    total = len(txns)
    return {
        "matched": matched_count,
        "unmatched": unmatched_count,
        "total": total,
        "msg": (
            f"AI matching complete. {matched_count} of {total} transactions received suggestions."
        ),
    }


# ─── 7. Confirm a match ───────────────────────────────────────────────────────

@router.put("/transactions/{transaction_id}/confirm")
def confirm_transaction(
    transaction_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Confirm an AI-suggested (or manual) match for a transaction.

    Body fields (all optional):
      matched_invoice_id, matched_vendor_id, matched_category_id, mark_paid (bool)

    If matched_invoice_id is provided and the invoice is 'unpaid', pass mark_paid=true
    to simultaneously mark the invoice as paid.
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_WRITE_ROLES)

    txn = db.query(BankFeedTransaction).filter(
        BankFeedTransaction.id == transaction_id,
        BankFeedTransaction.org_id == current_user.org_id,
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    matched_invoice_id = body.get("matched_invoice_id")
    matched_vendor_id = body.get("matched_vendor_id")
    matched_category_id = body.get("matched_category_id")
    mark_paid = bool(body.get("mark_paid", False))

    txn.matched_invoice_id = matched_invoice_id
    txn.matched_vendor_id = matched_vendor_id
    txn.matched_category_id = matched_category_id
    txn.status = "confirmed"

    invoice_updated = False
    if matched_invoice_id and mark_paid:
        # Optionally mark the linked invoice as paid
        result = db.execute(
            text(
                "UPDATE invoices SET payment_status='paid' "
                "WHERE id=:iid AND org_id=:oid AND payment_status='unpaid'"
            ),
            {"iid": matched_invoice_id, "oid": current_user.org_id},
        )
        invoice_updated = result.rowcount > 0

    db.commit()

    return {
        "msg": "Transaction confirmed.",
        "transaction_id": transaction_id,
        "status": "confirmed",
        "invoice_marked_paid": invoice_updated,
    }


# ─── 8. Exclude a transaction ─────────────────────────────────────────────────

@router.put("/transactions/{transaction_id}/exclude")
def exclude_transaction(
    transaction_id: int,
    body: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Mark a transaction as excluded (internal transfer, owner draw, payroll, ATM, etc.).

    Optionally pass notes explaining the exclusion reason.
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_WRITE_ROLES)

    txn = db.query(BankFeedTransaction).filter(
        BankFeedTransaction.id == transaction_id,
        BankFeedTransaction.org_id == current_user.org_id,
    ).first()
    if not txn:
        raise HTTPException(status_code=404, detail="Transaction not found")

    txn.status = "excluded"
    if body.get("notes"):
        txn.notes = body["notes"]

    db.commit()
    return {"msg": "Transaction excluded.", "transaction_id": transaction_id}


# ─── 9. Reconciliation summary ────────────────────────────────────────────────

@router.get("/reconciliation-summary")
def reconciliation_summary(
    connection_id: Optional[int] = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Reconciliation summary for the org (or a specific connection).

    Returns:
      - total_debits: sum of negative-amount transactions (money out)
      - total_credits: sum of positive-amount transactions (money in)
      - matched_amount: sum of amounts with status 'confirmed'
      - unmatched_amount: sum of amounts with status 'unmatched'
      - count_by_status: breakdown of transaction counts per status
      - unmatched_invoices: count of unpaid invoices not yet linked to a confirmed transaction
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)

    org_id = current_user.org_id

    base_filter = "org_id=:oid"
    params: dict = {"oid": org_id}

    if connection_id:
        base_filter += " AND connection_id=:cid"
        params["cid"] = connection_id

    rows = db.execute(
        text(
            f"SELECT status, amount FROM bank_feed_transactions WHERE {base_filter}"
        ),
        params,
    ).fetchall()

    total_debits = 0.0
    total_credits = 0.0
    matched_amount = 0.0
    unmatched_amount = 0.0
    ai_suggested_amount = 0.0
    count_by_status: dict = {
        "unmatched": 0,
        "ai_suggested": 0,
        "confirmed": 0,
        "excluded": 0,
    }

    for row in rows:
        status_val, amount = row[0], float(row[1] or 0)
        if amount < 0:
            total_debits += abs(amount)
        else:
            total_credits += amount

        if status_val in count_by_status:
            count_by_status[status_val] += 1

        if status_val == "confirmed":
            matched_amount += abs(amount)
        elif status_val == "unmatched":
            unmatched_amount += abs(amount)
        elif status_val == "ai_suggested":
            ai_suggested_amount += abs(amount)

    # Count unpaid invoices that have no confirmed bank feed transaction linked
    unmatched_invoices_row = db.execute(
        text(
            "SELECT COUNT(*) FROM invoices "
            "WHERE org_id=:oid AND payment_status='unpaid' "
            "AND id NOT IN ("
            "  SELECT matched_invoice_id FROM bank_feed_transactions "
            "  WHERE org_id=:oid2 AND status='confirmed' AND matched_invoice_id IS NOT NULL"
            ")"
        ),
        {"oid": org_id, "oid2": org_id},
    ).fetchone()
    unmatched_invoices = unmatched_invoices_row[0] if unmatched_invoices_row else 0

    return {
        "total_debits": round(total_debits, 2),
        "total_credits": round(total_credits, 2),
        "matched_amount": round(matched_amount, 2),
        "unmatched_amount": round(unmatched_amount, 2),
        "ai_suggested_amount": round(ai_suggested_amount, 2),
        "count_by_status": count_by_status,
        "total_transactions": len(rows),
        "unmatched_invoices": unmatched_invoices,
    }
