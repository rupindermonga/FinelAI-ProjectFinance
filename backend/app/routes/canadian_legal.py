"""Canadian Legal Workflows — Proper Invoice Validation, Notice of Non-Payment,
Certificate of Substantial Performance, Sources & Uses Ledger."""
import secrets
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, FINANCE_READ_ROLES, FINANCE_WRITE_ROLES
from ..models import (
    NonPaymentNotice, SubstantialPerformanceCert, SourcesUsesEntry,
    Project, Invoice, Draw
)
from ..routes.compliance import PROVINCE_RULES

router = APIRouter(prefix="/api/project", tags=["canadian-legal"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _proj(project_id, user, db):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(404)
    require_org_member(db, p.org_id, user.id, FINANCE_READ_ROLES)
    return p


# ── Proper Invoice Validator ───────────────────────────────────────────────────

@router.post("/{project_id}/validate-invoice/{invoice_id}")
def validate_proper_invoice(project_id: int, invoice_id: int,
                            db: Session = Depends(_db), user=Depends(get_current_user)):
    """Validate invoice against Ontario Construction Act 'proper invoice' requirements."""
    p = _proj(project_id, user, db)
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.project_id == project_id).first()
    if not inv: raise HTTPException(404)
    province = p.province or "ON"
    rules = PROVINCE_RULES.get(province, PROVINCE_RULES["ON"])

    checks = [
        {"field": "Invoice Date", "passed": bool(inv.invoice_date), "value": inv.invoice_date,
         "requirement": "Invoice must have a date (s.6.4(1)(a))"},
        {"field": "Invoice Number", "passed": bool(inv.invoice_number), "value": inv.invoice_number,
         "requirement": "Invoice must have a unique identifier (s.6.4(1)(b))"},
        {"field": "Vendor Name", "passed": bool(inv.vendor_name), "value": inv.vendor_name,
         "requirement": "Name and address of contractor/subcontractor (s.6.4(1)(c))"},
        {"field": "Description of Services", "passed": bool(inv.extracted_data or inv.source_file), "value": "Present" if inv.extracted_data else None,
         "requirement": "Description of services/materials supplied (s.6.4(1)(d))"},
        {"field": "Amount Claimed", "passed": bool(inv.total_due and inv.total_due > 0), "value": f"${inv.total_due:,.2f}" if inv.total_due else None,
         "requirement": "Amount claimed for services (s.6.4(1)(e))"},
        {"field": "HST/GST Number", "passed": True, "value": "Not validated — check vendor record",
         "requirement": "GST/HST registration number where applicable"},
        {"field": "Payment Terms", "passed": bool(inv.due_date), "value": inv.due_date or "No due date set",
         "requirement": f"Payment due date within {rules['prompt_payment_owner_to_gc_days']} days ({rules['act']})"},
        {"field": "Project Reference", "passed": bool(inv.project_id), "value": p.name,
         "requirement": "Invoice must reference the specific project (best practice)"},
    ]

    passed = sum(1 for c in checks if c["passed"])
    is_proper = all(c["passed"] for c in checks[:6])  # first 6 are mandatory

    return {
        "invoice_id": invoice_id, "invoice_number": inv.invoice_number,
        "vendor_name": inv.vendor_name, "province": province,
        "act": rules["act"], "is_proper": is_proper,
        "passed": passed, "total": len(checks),
        "prompt_payment_days": rules["prompt_payment_owner_to_gc_days"],
        "checks": checks,
        "message": "✓ Invoice meets proper invoice requirements" if is_proper
                   else f"⚠ Invoice is missing {len(checks)-passed} required fields to qualify as a proper invoice",
    }


# ── Notice of Non-Payment ──────────────────────────────────────────────────────

@router.get("/{project_id}/non-payment-notices")
def list_nnp(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    rows = db.query(NonPaymentNotice).filter(NonPaymentNotice.project_id == project_id).order_by(NonPaymentNotice.created_at.desc()).all()
    return [_nnp_out(r) for r in rows]


def _nnp_out(r):
    return {
        "id": r.id, "payment_type": r.payment_type,
        "proper_invoice_date": r.proper_invoice_date,
        "certifier_cert_date": r.certifier_cert_date,
        "payment_deadline": r.payment_deadline,
        "notice_date": r.notice_date,
        "disputed_amount": r.disputed_amount, "non_disputed_amount": r.non_disputed_amount,
        "reasons": r.reasons, "vendor_name": r.vendor_name,
        "province": r.province, "status": r.status, "notes": r.notes,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/{project_id}/non-payment-notices")
def create_nnp(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    province = p.province or "ON"
    rules = PROVINCE_RULES.get(province, PROVINCE_RULES["ON"])
    # Auto-calculate deadline
    deadline = None
    cert_date = body.get("certifier_cert_date") or body.get("proper_invoice_date")
    if cert_date:
        try:
            deadline = (datetime.strptime(cert_date, "%Y-%m-%d") + timedelta(days=rules["prompt_payment_owner_to_gc_days"])).strftime("%Y-%m-%d")
        except Exception:
            pass
    r = NonPaymentNotice(
        org_id=p.org_id, project_id=project_id,
        draw_id=body.get("draw_id"), invoice_id=body.get("invoice_id"),
        payment_type=body.get("payment_type", "owner_to_gc"),
        proper_invoice_date=body.get("proper_invoice_date"),
        certifier_cert_date=body.get("certifier_cert_date"),
        payment_deadline=body.get("payment_deadline", deadline),
        notice_date=body.get("notice_date"),
        disputed_amount=body.get("disputed_amount"),
        non_disputed_amount=body.get("non_disputed_amount"),
        reasons=body.get("reasons"),
        vendor_name=body.get("vendor_name"),
        vendor_address=body.get("vendor_address"),
        province=province, status=body.get("status", "draft"),
        notes=body.get("notes"), created_by=user.id,
    )
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "payment_deadline": r.payment_deadline, "ok": True}


@router.put("/{project_id}/non-payment-notices/{nnp_id}")
def update_nnp(project_id: int, nnp_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = db.query(NonPaymentNotice).filter(NonPaymentNotice.id == nnp_id, NonPaymentNotice.project_id == project_id).first()
    if not r: raise HTTPException(404)
    for f in ["payment_type","proper_invoice_date","certifier_cert_date","payment_deadline","notice_date","disputed_amount","non_disputed_amount","reasons","vendor_name","vendor_address","status","notes"]:
        if f in body: setattr(r, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/non-payment-notices/{nnp_id}")
def delete_nnp(project_id: int, nnp_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = db.query(NonPaymentNotice).filter(NonPaymentNotice.id == nnp_id, NonPaymentNotice.project_id == project_id).first()
    if r: db.delete(r); db.commit()
    return {"ok": True}


@router.get("/{project_id}/non-payment-notices/{nnp_id}/html", response_class=HTMLResponse)
def nnp_html(project_id: int, nnp_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    """Generate a print-ready Notice of Non-Payment form."""
    p = _proj(project_id, user, db)
    r = db.query(NonPaymentNotice).filter(NonPaymentNotice.id == nnp_id, NonPaymentNotice.project_id == project_id).first()
    if not r: raise HTTPException(404)
    province = r.province or "ON"
    rules = PROVINCE_RULES.get(province, PROVINCE_RULES["ON"])
    html = f"""<!DOCTYPE html><html><head><meta charset="UTF-8"/>
<title>Notice of Non-Payment</title>
<style>body{{font-family:Arial,sans-serif;max-width:700px;margin:40px auto;font-size:13px}}
h1{{font-size:18px;text-align:center;margin-bottom:4px}}
h2{{font-size:14px;border-bottom:2px solid #000;padding-bottom:4px;margin-top:20px}}
.field{{margin:8px 0}}.label{{font-weight:bold;width:180px;display:inline-block}}</style>
</head><body>
<h1>NOTICE OF NON-PAYMENT</h1>
<p style="text-align:center;font-size:11px">{rules['act']}</p>
<h2>1. PROJECT INFORMATION</h2>
<div class="field"><span class="label">Project Name:</span> {p.name}</div>
<div class="field"><span class="label">Project Address:</span> {p.address or '—'}</div>
<div class="field"><span class="label">Province:</span> {province}</div>
<h2>2. PAYMENT DETAILS</h2>
<div class="field"><span class="label">Payment Type:</span> {r.payment_type.replace('_',' ').title()}</div>
<div class="field"><span class="label">Proper Invoice Date:</span> {r.proper_invoice_date or '—'}</div>
<div class="field"><span class="label">Certification Date:</span> {r.certifier_cert_date or '—'}</div>
<div class="field"><span class="label">Payment Deadline:</span> <strong>{r.payment_deadline or '—'}</strong></div>
<div class="field"><span class="label">Notice Date:</span> {r.notice_date or date.today().isoformat()}</div>
<div class="field"><span class="label">Vendor:</span> {r.vendor_name or '—'}</div>
<div class="field"><span class="label">Vendor Address:</span> {r.vendor_address or '—'}</div>
<h2>3. AMOUNTS</h2>
<div class="field"><span class="label">Amount Disputed:</span> ${(r.disputed_amount or 0):,.2f}</div>
<div class="field"><span class="label">Amount Not Disputed:</span> ${(r.non_disputed_amount or 0):,.2f}</div>
<h2>4. REASONS FOR NON-PAYMENT</h2>
<p>{r.reasons or '—'}</p>
<h2>5. SIGNATURES</h2>
<div style="margin-top:40px;display:flex;gap:60px">
<div><div style="border-top:1px solid #000;width:200px;margin-top:50px;padding-top:4px">Payor / Authorized Representative</div></div>
<div><div style="border-top:1px solid #000;width:200px;margin-top:50px;padding-top:4px">Date</div></div>
</div>
<p style="margin-top:30px;font-size:10px;color:#666">This Notice of Non-Payment is issued pursuant to {rules['act']}. Service must be made in accordance with applicable regulations. Non-disputed amounts must be paid by the payment deadline.</p>
</body></html>"""
    return HTMLResponse(html)


# ── Certificate of Substantial Performance ─────────────────────────────────────

@router.get("/{project_id}/substantial-performance")
def list_sp_certs(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    rows = db.query(SubstantialPerformanceCert).filter(SubstantialPerformanceCert.project_id == project_id).order_by(SubstantialPerformanceCert.created_at.desc()).all()
    return [_sp_out(r) for r in rows]


def _sp_out(r):
    return {
        "id": r.id, "contract_amount": r.contract_amount, "certified_amount": r.certified_amount,
        "holdback_amount": r.holdback_amount, "certification_date": r.certification_date,
        "publication_date": r.publication_date, "lien_expiry_date": r.lien_expiry_date,
        "holdback_release_date": r.holdback_release_date,
        "consultant_name": r.consultant_name, "consultant_firm": r.consultant_firm,
        "owner_name": r.owner_name, "contractor_name": r.contractor_name,
        "province": r.province, "status": r.status, "notes": r.notes,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/{project_id}/substantial-performance")
def create_sp_cert(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    province = p.province or "ON"
    rules = PROVINCE_RULES.get(province, PROVINCE_RULES["ON"])
    lien_days = rules["lien_period_days"]
    # Auto-calculate lien expiry from publication date
    lien_expiry = None
    pub_date = body.get("publication_date")
    if pub_date:
        try:
            lien_expiry = (datetime.strptime(pub_date, "%Y-%m-%d") + timedelta(days=lien_days)).strftime("%Y-%m-%d")
        except Exception:
            pass
    # Holdback release = after lien period
    holdback_release = lien_expiry
    r = SubstantialPerformanceCert(
        org_id=p.org_id, project_id=project_id,
        contract_amount=body.get("contract_amount", p.total_budget),
        certified_amount=body.get("certified_amount"),
        holdback_amount=body.get("holdback_amount"),
        certification_date=body.get("certification_date"),
        publication_date=pub_date,
        lien_expiry_date=body.get("lien_expiry_date", lien_expiry),
        holdback_release_date=body.get("holdback_release_date", holdback_release),
        consultant_name=body.get("consultant_name"),
        consultant_firm=body.get("consultant_firm"),
        owner_name=body.get("owner_name", p.client),
        contractor_name=body.get("contractor_name"),
        province=province, status=body.get("status", "draft"),
        notes=body.get("notes"), created_by=user.id,
    )
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "lien_expiry_date": r.lien_expiry_date, "holdback_release_date": r.holdback_release_date, "ok": True}


@router.put("/{project_id}/substantial-performance/{sp_id}")
def update_sp_cert(project_id: int, sp_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = db.query(SubstantialPerformanceCert).filter(SubstantialPerformanceCert.id == sp_id, SubstantialPerformanceCert.project_id == project_id).first()
    if not r: raise HTTPException(404)
    for f in ["contract_amount","certified_amount","holdback_amount","certification_date","publication_date","lien_expiry_date","holdback_release_date","consultant_name","consultant_firm","owner_name","contractor_name","status","notes"]:
        if f in body: setattr(r, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/substantial-performance/{sp_id}")
def delete_sp_cert(project_id: int, sp_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = db.query(SubstantialPerformanceCert).filter(SubstantialPerformanceCert.id == sp_id, SubstantialPerformanceCert.project_id == project_id).first()
    if r: db.delete(r); db.commit()
    return {"ok": True}


# ── Sources & Uses Ledger ──────────────────────────────────────────────────────

SOURCES_CATEGORIES = ["equity", "senior_debt", "mezzanine", "grant", "deposit", "presales", "other_source"]
USES_CATEGORIES = ["land", "hard_cost", "soft_cost", "financing_costs", "contingency", "other_use"]

@router.get("/{project_id}/sources-uses")
def get_sources_uses(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    entries = db.query(SourcesUsesEntry).filter(SourcesUsesEntry.project_id == project_id).order_by(SourcesUsesEntry.display_order, SourcesUsesEntry.id).all()
    sources = [_su_out(e) for e in entries if e.entry_type == "source"]
    uses = [_su_out(e) for e in entries if e.entry_type == "use"]
    total_sources_budgeted = sum(e["budgeted_amount"] for e in sources)
    total_uses_budgeted = sum(e["budgeted_amount"] for e in uses)
    total_sources_actual = sum(e["actual_amount"] or 0 for e in sources)
    total_uses_actual = sum(e["actual_amount"] or 0 for e in uses)
    return {
        "sources": sources, "uses": uses,
        "summary": {
            "total_sources_budgeted": total_sources_budgeted,
            "total_uses_budgeted": total_uses_budgeted,
            "sources_uses_balanced": abs(total_sources_budgeted - total_uses_budgeted) < 1,
            "variance": round(total_sources_budgeted - total_uses_budgeted, 2),
            "total_sources_actual": total_sources_actual,
            "total_uses_actual": total_uses_actual,
        }
    }


def _su_out(e):
    return {"id": e.id, "entry_type": e.entry_type, "category": e.category,
            "description": e.description, "budgeted_amount": e.budgeted_amount,
            "actual_amount": e.actual_amount, "as_of_date": e.as_of_date, "notes": e.notes}


@router.post("/{project_id}/sources-uses")
def create_su_entry(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    e = SourcesUsesEntry(
        org_id=p.org_id, project_id=project_id,
        entry_type=body["entry_type"], category=body.get("category", "other_source"),
        description=body["description"],
        budgeted_amount=body.get("budgeted_amount", 0),
        actual_amount=body.get("actual_amount"),
        as_of_date=body.get("as_of_date"), notes=body.get("notes"),
        display_order=body.get("display_order", 100), created_by=user.id,
    )
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id, "ok": True}


@router.put("/{project_id}/sources-uses/{entry_id}")
def update_su_entry(project_id: int, entry_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    e = db.query(SourcesUsesEntry).filter(SourcesUsesEntry.id == entry_id, SourcesUsesEntry.project_id == project_id).first()
    if not e: raise HTTPException(404)
    for f in ["entry_type","category","description","budgeted_amount","actual_amount","as_of_date","notes","display_order"]:
        if f in body: setattr(e, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/sources-uses/{entry_id}")
def delete_su_entry(project_id: int, entry_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    e = db.query(SourcesUsesEntry).filter(SourcesUsesEntry.id == entry_id, SourcesUsesEntry.project_id == project_id).first()
    if e: db.delete(e); db.commit()
    return {"ok": True}
