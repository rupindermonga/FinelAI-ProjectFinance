"""
Phase 10 — Platform API Features
- AI Document Q&A: RAG over project RFIs, submittals, meetings, daily logs, spec reviews
- EFT / CPA Standard 005 payment file generation
- API Keys management (public REST API access)
- Webhook registry + delivery log
"""
from __future__ import annotations

import os
import io
import csv
import hmac
import hashlib
import json
import secrets
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, FINANCE_READ_ROLES, call_gemini_api
from ..models import APIKey, Webhook, WebhookDelivery, EFTBatch, EFTBatchPayment, User

router = APIRouter(prefix="/api", tags=["platform"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── AI Document Q&A (RAG over project documents) ────────────────────────────

@router.post("/project/{project_id}/doc-qa")
async def doc_qa(project_id: int, body: dict,
                 db: Session = Depends(get_db),
                 current_user: User = Depends(get_current_user)):
    """
    Answer questions about a project using Gemini, grounded in actual project data.
    Sources: RFIs, Submittals, Meeting Minutes, Daily Logs, Spec Reviews, Change Orders.
    """
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    question = body.get("question", "").strip()
    if not question:
        raise HTTPException(400, "question is required")

    # Gather project context from DB (latest 150 records across key tables)
    context_parts = []

    # RFIs
    rfis = db.execute(text("""
        SELECT rfi_number, subject, description, status, response, due_date
        FROM pm_rfis WHERE project_id=:pid ORDER BY created_at DESC LIMIT 40
    """), {"pid": project_id}).fetchall()
    if rfis:
        context_parts.append("=== RFIs ===")
        for r in rfis:
            context_parts.append(f"RFI {r[0]}: {r[1]} | Status: {r[3]} | Due: {r[5]}\nDesc: {r[2] or ''}\nResponse: {r[4] or ''}")

    # Submittals
    subs = db.execute(text("""
        SELECT submittal_number, title, spec_section, status, review_notes, submitted_date
        FROM pm_submittals WHERE project_id=:pid ORDER BY created_at DESC LIMIT 40
    """), {"pid": project_id}).fetchall()
    if subs:
        context_parts.append("=== Submittals ===")
        for s in subs:
            context_parts.append(f"Submittal {s[0]}: {s[1]} | Spec: {s[2]} | Status: {s[3]}\nNotes: {s[5] or ''}")

    # Meeting Minutes
    meetings = db.execute(text("""
        SELECT title, meeting_date, minutes, action_items
        FROM pm_meetings WHERE project_id=:pid ORDER BY meeting_date DESC LIMIT 20
    """), {"pid": project_id}).fetchall()
    if meetings:
        context_parts.append("=== Meeting Minutes ===")
        for m in meetings:
            context_parts.append(f"Meeting: {m[0]} on {m[1]}\nMinutes: {m[2] or ''}\nAction Items: {m[3] or ''}")

    # Daily Logs (last 30)
    logs = db.execute(text("""
        SELECT log_date, weather, work_summary, issues, delays
        FROM pm_daily_logs WHERE project_id=:pid ORDER BY log_date DESC LIMIT 30
    """), {"pid": project_id}).fetchall()
    if logs:
        context_parts.append("=== Daily Site Logs ===")
        for l in logs:
            context_parts.append(f"Date: {l[0]} | Weather: {l[1]}\nWork: {l[2] or ''}\nIssues: {l[3] or ''}\nDelays: {l[4] or ''}")

    # Change Orders
    cos = db.execute(text("""
        SELECT co_number, description, amount, status, date
        FROM change_orders WHERE project_id=:pid ORDER BY date DESC LIMIT 30
    """), {"pid": project_id}).fetchall()
    if cos:
        context_parts.append("=== Change Orders ===")
        for c in cos:
            context_parts.append(f"CO {c[0]}: {c[1]} | Amount: ${c[2]:,.2f} | Status: {c[3]} | Date: {c[4]}")

    # Spec Reviews (summaries)
    spec_reviews = db.execute(text("""
        SELECT filename, summary, total_issues, created_at
        FROM spec_reviews WHERE project_id=:pid ORDER BY created_at DESC LIMIT 5
    """), {"pid": project_id}).fetchall()
    if spec_reviews:
        context_parts.append("=== Spec Reviews ===")
        for s in spec_reviews:
            context_parts.append(f"File: {s[0]} | Issues: {s[2]} | Reviewed: {s[3]}\nSummary: {s[1] or ''}")

    context_text = "\n\n".join(context_parts)
    if not context_text.strip():
        context_text = "No project documents found."

    prompt = f"""You are an expert construction project assistant. Answer the following question using ONLY the project data provided below.
If the answer is not in the data, say so clearly. Always cite which document/record you are drawing from.
Include any relevant dates, numbers, or statuses from the data.

PROJECT DATA:
{context_text[:28000]}

QUESTION: {question}

Provide a clear, direct answer with specific references to the source documents."""

    result = await call_gemini_api(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.2, "maxOutputTokens": 2048},
        },
        timeout=60,
    )
    answer = result["candidates"][0]["content"]["parts"][0]["text"]
    sources_used = []
    if rfis: sources_used.append(f"{len(rfis)} RFIs")
    if subs: sources_used.append(f"{len(subs)} Submittals")
    if meetings: sources_used.append(f"{len(meetings)} Meeting Minutes")
    if logs: sources_used.append(f"{len(logs)} Daily Logs")
    if cos: sources_used.append(f"{len(cos)} Change Orders")
    if spec_reviews: sources_used.append(f"{len(spec_reviews)} Spec Reviews")

    return {
        "answer": answer,
        "sources_searched": sources_used,
        "question": question,
    }


# ─── EFT / CPA-005 Payment File Generation ───────────────────────────────────

@router.get("/eft-batches")
def list_eft_batches(db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    rows = (db.query(EFTBatch)
            .filter(EFTBatch.org_id == current_user.org_id)
            .order_by(EFTBatch.created_at.desc())
            .limit(100).all())
    return [{k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"} for r in rows]


@router.post("/eft-batches")
def create_eft_batch(body: dict, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    payments_data = body.pop("payments", [])
    batch = EFTBatch(
        org_id=current_user.org_id, created_by=current_user.id,
        **{k: v for k, v in body.items() if hasattr(EFTBatch, k)}
    )
    db.add(batch)
    db.flush()
    total = 0.0
    for p in payments_data:
        amt = p.get("amount", 0) or 0
        total += amt
        db.add(EFTBatchPayment(
            batch_id=batch.id, org_id=current_user.org_id,
            **{k: v for k, v in p.items() if hasattr(EFTBatchPayment, k) and k not in ("id", "batch_id", "amount")},
            amount=amt
        ))
    batch.total_amount = total
    batch.payment_count = len(payments_data)
    db.commit()
    db.refresh(batch)
    return {"id": batch.id, "total_amount": batch.total_amount, "payment_count": batch.payment_count, "msg": "EFT batch created"}


@router.get("/eft-batches/{batch_id}")
def get_eft_batch(batch_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    batch = db.query(EFTBatch).filter(EFTBatch.id == batch_id,
                                      EFTBatch.org_id == current_user.org_id).first()
    if not batch:
        raise HTTPException(404)
    d = {k: v for k, v in batch.__dict__.items() if k != "_sa_instance_state"}
    d["payments"] = [{k: v for k, v in p.__dict__.items() if k != "_sa_instance_state"} for p in batch.payments]
    return d


@router.delete("/eft-batches/{batch_id}")
def delete_eft_batch(batch_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    batch = db.query(EFTBatch).filter(EFTBatch.id == batch_id,
                                      EFTBatch.org_id == current_user.org_id).first()
    if not batch:
        raise HTTPException(404)
    if batch.status not in ("draft", "generated", "failed"):
        raise HTTPException(400, "Only draft, generated, or failed batches can be deleted")
    db.delete(batch)
    db.commit()
    return {"msg": "deleted"}


@router.post("/eft-batches/{batch_id}/add-payment")
def add_eft_payment(batch_id: int, body: dict,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    batch = db.query(EFTBatch).filter(EFTBatch.id == batch_id,
                                      EFTBatch.org_id == current_user.org_id).first()
    if not batch or batch.status != "draft":
        raise HTTPException(400, "Batch not found or not in draft status")
    payment = EFTBatchPayment(
        batch_id=batch_id, org_id=current_user.org_id,
        **{k: v for k, v in body.items() if hasattr(EFTBatchPayment, k)}
    )
    db.add(payment)
    batch.total_amount = (batch.total_amount or 0) + (payment.amount or 0)
    batch.payment_count = (batch.payment_count or 0) + 1
    db.commit()
    return {"id": payment.id, "msg": "payment added"}


@router.get("/eft-batches/{batch_id}/download")
def download_eft_file(batch_id: int, db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    """Generate CPA Standard 005 (1464-byte fixed-width EFT) file."""
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    batch = db.query(EFTBatch).filter(EFTBatch.id == batch_id,
                                      EFTBatch.org_id == current_user.org_id).first()
    if not batch:
        raise HTTPException(404)

    # CPA 005 format — simplified 1464-character record structure
    originator_id = (batch.originator_id or "FINEL0001").ljust(10)[:10]
    value_date = (batch.value_date or datetime.now().strftime("%Y-%m-%d")).replace("-", "")[:6]  # YYMMDD

    lines = []
    # Header record (Type "A")
    lines.append(
        f"A{'0' * 9}{originator_id}"
        f"{value_date}"
        f"{'CAD'}"
        f"{' ' * 1430}"
    )

    total_credit_cents = 0
    for i, pmt in enumerate(batch.payments, 1):
        amt_cents = int((pmt.amount or 0) * 100)
        total_credit_cents += amt_cents
        transit = (pmt.payee_bank_transit or "00000").zfill(5)[:5]
        institution = (pmt.payee_bank_institution or "000").zfill(3)[:3]
        account = (pmt.payee_bank_account or "000000000").ljust(12)[:12]
        payee = (pmt.payee_name or "UNKNOWN").ljust(30)[:30]
        memo = (pmt.memo or "").ljust(19)[:19]
        lines.append(
            f"C{str(i).zfill(7)}"
            f"{transit}{institution}"
            f"{account}"
            f"{str(amt_cents).zfill(10)}"
            f"{payee}"
            f"{originator_id}"
            f"{memo}"
            f"{' ' * 1360}"
        )

    # Trailer record (Type "Z")
    lines.append(
        f"Z{' ' * 9}{originator_id}"
        f"{str(len(batch.payments)).zfill(8)}"
        f"{str(total_credit_cents).zfill(14)}"
        f"{'0' * 14}"  # debit total = 0
        f"{' ' * 1410}"
    )

    content = "\r\n".join(lines) + "\r\n"
    filename = f"EFT_Batch_{batch.batch_number}_{batch.value_date}.txt"

    # Mark batch as generated
    batch.status = "generated"
    db.commit()

    return StreamingResponse(
        io.BytesIO(content.encode("ascii")),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ─── API Keys ─────────────────────────────────────────────────────────────────

@router.get("/api-keys")
def list_api_keys(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    rows = (db.query(APIKey)
            .filter(APIKey.org_id == current_user.org_id)
            .order_by(APIKey.created_at.desc()).all())
    return [
        {
            "id": r.id, "name": r.name, "key_prefix": r.key_prefix,
            "scopes": r.scopes, "is_active": r.is_active,
            "last_used_at": r.last_used_at, "expires_at": r.expires_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/api-keys")
def create_api_key(body: dict, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    raw_key = "fai_" + secrets.token_urlsafe(32)
    prefix = raw_key[:12]
    from passlib.context import CryptContext
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    key_hash = pwd.hash(raw_key)
    api_key = APIKey(
        org_id=current_user.org_id,
        name=body.get("name", "API Key"),
        key_prefix=prefix,
        key_hash=key_hash,
        scopes=body.get("scopes", "read"),
        expires_at=body.get("expires_at"),
        created_by=current_user.id,
    )
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    return {
        "id": api_key.id,
        "name": api_key.name,
        "key": raw_key,  # shown ONCE — user must copy it now
        "key_prefix": prefix,
        "scopes": api_key.scopes,
        "msg": "API key created. Copy it now — it will not be shown again."
    }


@router.delete("/api-keys/{key_id}")
def delete_api_key(key_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    key = db.query(APIKey).filter(APIKey.id == key_id,
                                  APIKey.org_id == current_user.org_id).first()
    if not key:
        raise HTTPException(404)
    db.delete(key)
    db.commit()
    return {"msg": "API key revoked"}


@router.put("/api-keys/{key_id}/toggle")
def toggle_api_key(key_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    key = db.query(APIKey).filter(APIKey.id == key_id,
                                  APIKey.org_id == current_user.org_id).first()
    if not key:
        raise HTTPException(404)
    key.is_active = not key.is_active
    db.commit()
    return {"is_active": key.is_active}


# ─── Webhooks ─────────────────────────────────────────────────────────────────

SUPPORTED_EVENTS = [
    "invoice.created", "invoice.approved", "invoice.paid",
    "draw.submitted", "draw.approved", "draw.funded",
    "change_order.created", "change_order.approved",
    "rfi.created", "rfi.responded",
    "bid.awarded", "subcontract.signed",
    "safety.incident_reported",
    "project.status_changed",
]


@router.get("/webhooks")
def list_webhooks(db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    rows = (db.query(Webhook)
            .filter(Webhook.org_id == current_user.org_id)
            .order_by(Webhook.created_at.desc()).all())
    return [
        {
            "id": r.id, "name": r.name, "url": r.url,
            "events": r.events, "is_active": r.is_active,
            "failure_count": r.failure_count,
            "last_triggered_at": r.last_triggered_at,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.post("/webhooks")
def create_webhook(body: dict, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    url = body.get("url", "")
    if not url.startswith("https://"):
        raise HTTPException(400, "Webhook URL must use HTTPS")
    signing_secret = secrets.token_hex(32)
    wh = Webhook(
        org_id=current_user.org_id,
        name=body.get("name", "Webhook"),
        url=url,
        secret=signing_secret,
        events=body.get("events", "invoice.created"),
        created_by=current_user.id,
    )
    db.add(wh)
    db.commit()
    db.refresh(wh)
    return {
        "id": wh.id,
        "name": wh.name,
        "url": wh.url,
        "signing_secret": signing_secret,  # shown once
        "events": wh.events,
        "msg": "Webhook created. Save the signing secret — it will not be shown again."
    }


@router.put("/webhooks/{webhook_id}")
def update_webhook(webhook_id: int, body: dict,
                   db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    wh = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.org_id == current_user.org_id).first()
    if not wh:
        raise HTTPException(404)
    for k in ("name", "url", "events", "is_active"):
        if k in body:
            setattr(wh, k, body[k])
    db.commit()
    return {"msg": "updated"}


@router.delete("/webhooks/{webhook_id}")
def delete_webhook(webhook_id: int, db: Session = Depends(get_db),
                   current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    wh = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.org_id == current_user.org_id).first()
    if not wh:
        raise HTTPException(404)
    db.delete(wh)
    db.commit()
    return {"msg": "deleted"}


@router.get("/webhooks/{webhook_id}/deliveries")
def list_webhook_deliveries(webhook_id: int, db: Session = Depends(get_db),
                            current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    rows = (db.query(WebhookDelivery)
            .filter(WebhookDelivery.webhook_id == webhook_id,
                    WebhookDelivery.org_id == current_user.org_id)
            .order_by(WebhookDelivery.created_at.desc())
            .limit(50).all())
    return [{k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"} for r in rows]


@router.post("/webhooks/{webhook_id}/test")
async def test_webhook(webhook_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    """Send a test ping to the webhook endpoint."""
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    wh = db.query(Webhook).filter(Webhook.id == webhook_id,
                                  Webhook.org_id == current_user.org_id).first()
    if not wh:
        raise HTTPException(404)
    import httpx, time
    payload = {
        "event": "test.ping",
        "timestamp": datetime.utcnow().isoformat(),
        "data": {"message": "Webhook test from Finel AI Projects"},
    }
    payload_str = json.dumps(payload)
    sig = hmac.new(
        (wh.secret or "").encode(),
        payload_str.encode(),
        hashlib.sha256
    ).hexdigest() if wh.secret else ""

    start = time.monotonic()
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.post(
                wh.url,
                content=payload_str,
                headers={
                    "Content-Type": "application/json",
                    "X-Finel-Event": "test.ping",
                    "X-Finel-Signature": f"sha256={sig}",
                }
            )
        duration_ms = int((time.monotonic() - start) * 1000)
        success = 200 <= resp.status_code < 300
        delivery = WebhookDelivery(
            webhook_id=wh.id, org_id=current_user.org_id,
            event="test.ping", payload=payload_str,
            http_status=resp.status_code,
            response_body=resp.text[:500],
            duration_ms=duration_ms, success=success,
            delivered_at=datetime.utcnow() if success else None,
        )
        db.add(delivery)
        wh.last_triggered_at = datetime.utcnow()
        if not success:
            wh.failure_count = (wh.failure_count or 0) + 1
        db.commit()
        return {"success": success, "http_status": resp.status_code, "duration_ms": duration_ms}
    except Exception as e:
        db.add(WebhookDelivery(
            webhook_id=wh.id, org_id=current_user.org_id,
            event="test.ping", payload=payload_str, success=False,
            response_body=str(e),
        ))
        wh.failure_count = (wh.failure_count or 0) + 1
        db.commit()
        raise HTTPException(502, f"Webhook delivery failed: {e}")


@router.get("/webhooks/events")
def list_supported_events():
    """Return supported webhook event types."""
    return {"events": SUPPORTED_EVENTS}
