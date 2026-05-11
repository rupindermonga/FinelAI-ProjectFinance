"""AI Risk Scoring — project distress prediction, subcontractor default risk, portfolio dashboard."""
import os
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session
from sqlalchemy import func

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, get_current_org, FINANCE_READ_ROLES, call_gemini_api
from ..models import (
    Project, Draw, Invoice, CostCategory, ChangeOrder, CommittedCost,
    OrgVendor, Task, RFI, PunchItem, LenderCovenant, InterestReserve, InterestReserveDraw,
    BidPackage, Organization, OrganizationMember,
)

router = APIRouter(prefix="/api/project", tags=["ai-risk"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_project(project_id: int, user, db: Session) -> Project:
    proj = db.query(Project).filter(Project.id == project_id).first()
    if not proj:
        raise HTTPException(404)
    require_org_member(db, proj.org_id, user.id, FINANCE_READ_ROLES)
    return proj


# ── AI Risk Score ───────────────────────────────────────────────────────────────

@router.get("/{project_id}/ai-risk-score")
def ai_risk_score(project_id: int, db: Session = Depends(get_db),
                  user=Depends(get_current_user)):
    """Compute a 0–100 project risk score across 8 dimensions. Lower = riskier."""
    proj = _get_project(project_id, user, db)
    today = date.today().isoformat()

    scores = {}
    details = {}

    # 1. Budget risk (invoiced vs budget)
    invoices = db.query(Invoice).filter(Invoice.project_id == project_id, Invoice.status == "processed").all()
    total_invoiced = sum(i.lender_submitted_amt or i.total_due or 0 for i in invoices)
    budget = proj.total_budget or 0
    approved_cos = db.query(ChangeOrder).filter(ChangeOrder.project_id == project_id, ChangeOrder.status == "approved").all()
    revised_budget = budget + sum(c.amount for c in approved_cos)
    if revised_budget > 0:
        budget_pct = total_invoiced / revised_budget
        if budget_pct < 0.5:
            scores["budget"] = 90
        elif budget_pct < 0.8:
            scores["budget"] = 75
        elif budget_pct < 1.0:
            scores["budget"] = 55
        elif budget_pct < 1.1:
            scores["budget"] = 30
        else:
            scores["budget"] = 10
        details["budget"] = {"invoiced_pct": round(budget_pct * 100, 1), "revised_budget": revised_budget, "total_invoiced": total_invoiced}
    else:
        scores["budget"] = 70
        details["budget"] = {"note": "No budget set"}

    # 2. Schedule risk (end date vs today)
    if proj.end_date:
        days_remaining = (datetime.strptime(proj.end_date, "%Y-%m-%d").date() - date.today()).days
        if days_remaining > 60:
            scores["schedule"] = 85
        elif days_remaining > 14:
            scores["schedule"] = 65
        elif days_remaining >= 0:
            scores["schedule"] = 40
        else:
            scores["schedule"] = 15
        details["schedule"] = {"end_date": proj.end_date, "days_remaining": days_remaining}
    else:
        scores["schedule"] = 60
        details["schedule"] = {"note": "No end date set"}

    # 3. Draw cadence risk (time since last approved draw)
    draws = db.query(Draw).filter(Draw.project_id == project_id, Draw.status == "approved").order_by(Draw.submission_date.desc()).all()
    if draws:
        last_draw_date = draws[0].submission_date or ""
        if last_draw_date:
            days_since = (date.today() - datetime.strptime(last_draw_date, "%Y-%m-%d").date()).days
            scores["draw_cadence"] = 90 if days_since < 30 else (65 if days_since < 60 else (40 if days_since < 90 else 20))
            details["draw_cadence"] = {"last_approved_draw": last_draw_date, "days_since": days_since}
        else:
            scores["draw_cadence"] = 60
            details["draw_cadence"] = {}
    else:
        scores["draw_cadence"] = 50
        details["draw_cadence"] = {"note": "No approved draws"}

    # 4. Open RFI risk
    try:
        open_rfis = db.query(RFI).filter(RFI.project_id == project_id, RFI.status == "open").count()
        overdue_rfis = db.query(RFI).filter(RFI.project_id == project_id, RFI.status == "open", RFI.due_date < today).count()
        scores["rfi"] = 90 if open_rfis == 0 else (70 if open_rfis < 3 else (50 if open_rfis < 8 else 25))
        if overdue_rfis > 0:
            scores["rfi"] = max(10, scores["rfi"] - 20)
        details["rfi"] = {"open": open_rfis, "overdue": overdue_rfis}
    except Exception:
        scores["rfi"] = 70

    # 5. Covenant compliance
    try:
        covenants = db.query(LenderCovenant).filter(LenderCovenant.project_id == project_id).all()
        breaches = sum(1 for c in covenants if c.status == "breach")
        warnings = sum(1 for c in covenants if c.status == "warning")
        scores["covenants"] = 95 if not covenants else (90 if breaches == 0 and warnings == 0 else (60 if breaches == 0 else 15))
        details["covenants"] = {"total": len(covenants), "breaches": breaches, "warnings": warnings}
    except Exception:
        scores["covenants"] = 70

    # 6. Interest reserve health
    try:
        reserve = db.query(InterestReserve).filter(InterestReserve.project_id == project_id).first()
        if reserve:
            drawn = sum(d.amount for d in db.query(InterestReserveDraw).filter(InterestReserveDraw.reserve_id == reserve.id).all())
            pct = drawn / reserve.reserve_amount * 100 if reserve.reserve_amount else 0
            scores["interest_reserve"] = 90 if pct < 50 else (65 if pct < 75 else (35 if pct < 90 else 10))
            details["interest_reserve"] = {"pct_drawn": round(pct, 1)}
        else:
            scores["interest_reserve"] = 70
            details["interest_reserve"] = {"note": "No reserve tracked"}
    except Exception:
        scores["interest_reserve"] = 70

    # 7. Vendor compliance
    try:
        vendors = db.query(OrgVendor).filter(OrgVendor.org_id == proj.org_id, OrgVendor.is_active == True).all()
        critical = sum(1 for v in vendors if (v.wsib_expiry and v.wsib_expiry < today) or (v.insurance_expiry and v.insurance_expiry < today))
        scores["vendor_compliance"] = 90 if critical == 0 else (65 if critical < 2 else (40 if critical < 5 else 15))
        details["vendor_compliance"] = {"critical_expired": critical, "total_vendors": len(vendors)}
    except Exception:
        scores["vendor_compliance"] = 70

    # 8. Overdue invoice payments
    try:
        overdue = sum(1 for i in invoices if i.payment_status != "paid" and i.due_date and i.due_date < today)
        overdue_amt = sum(
            (i.lender_submitted_amt or i.total_due or 0) - (i.amount_paid or 0)
            for i in invoices if i.payment_status != "paid" and i.due_date and i.due_date < today
        )
        scores["payables"] = 90 if overdue == 0 else (70 if overdue < 3 else (45 if overdue < 10 else 20))
        details["payables"] = {"overdue_count": overdue, "overdue_amount": round(overdue_amt, 2)}
    except Exception:
        scores["payables"] = 70

    overall = round(sum(scores.values()) / len(scores))
    rag = "green" if overall >= 70 else ("amber" if overall >= 45 else "red")

    risk_flags = []
    if scores.get("budget", 100) < 40:
        risk_flags.append("Budget overrun risk — invoiced amount approaching or exceeding revised contract")
    if scores.get("covenants", 100) < 30:
        risk_flags.append("Covenant breach detected — lender action may be required")
    if scores.get("schedule", 100) < 30:
        risk_flags.append("Project past projected end date — delay risk")
    if scores.get("interest_reserve", 100) < 40:
        risk_flags.append("Interest reserve nearly depleted — potential funding gap")
    if scores.get("vendor_compliance", 100) < 40:
        risk_flags.append("Multiple vendors with expired insurance/WSIB — compliance exposure")
    if scores.get("rfi", 100) < 40:
        risk_flags.append("High number of open/overdue RFIs — design coordination risk")

    return {
        "overall_score": overall,
        "rag": rag,
        "risk_flags": risk_flags,
        "dimensions": scores,
        "details": details,
    }


# ── COI / ACORD OCR ────────────────────────────────────────────────────────────

@router.post("/{project_id}/vendors/{vendor_id}/parse-coi")
async def parse_coi(project_id: int, vendor_id: int, file: UploadFile = File(...),
                    db: Session = Depends(get_db), user=Depends(get_current_user)):
    """Use Gemini Vision to extract insurance fields from an ACORD certificate PDF/image."""
    import json
    import base64

    proj = _get_project(project_id, user, db)
    require_org_member(db, proj.org_id, user.id, FINANCE_READ_ROLES)
    vendor = db.query(OrgVendor).filter(OrgVendor.id == vendor_id, OrgVendor.org_id == proj.org_id).first()
    if not vendor:
        raise HTTPException(404, "Vendor not found")

    contents = await file.read()
    b64 = base64.b64encode(contents).decode()
    mime_type = file.content_type or "application/pdf"

    prompt = """Extract insurance certificate data from this ACORD certificate.
Return ONLY a JSON object with these fields (use null if not found):
{
  "insured_name": "...",
  "producer_name": "...",
  "gl_insurer": "General Liability insurer name",
  "gl_policy_number": "...",
  "gl_policy_start": "YYYY-MM-DD",
  "gl_policy_end": "YYYY-MM-DD",
  "gl_occurrence_limit": 2000000,
  "gl_aggregate_limit": 4000000,
  "auto_insurer": "...",
  "auto_policy_number": "...",
  "auto_policy_end": "YYYY-MM-DD",
  "umbrella_limit": null,
  "workers_comp_insurer": "...",
  "workers_comp_policy_end": "YYYY-MM-DD",
  "certificate_holder": "...",
  "certificate_date": "YYYY-MM-DD"
}
Return only valid JSON, no markdown."""

    try:
        result = await call_gemini_api(
            {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": mime_type, "data": b64}},
                    ]
                }],
                "generationConfig": {"temperature": 0.1},
            },
            timeout=60,
        )
        text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        if text.startswith("```"):
            text = "\n".join(text.split("\n")[1:])
            text = text.rsplit("```", 1)[0].strip()
        extracted = json.loads(text)
    except Exception as e:
        raise HTTPException(500, f"COI parsing failed: {str(e)}")

    # Auto-update vendor fields
    if extracted.get("gl_policy_end"):
        vendor.insurance_expiry = extracted["gl_policy_end"]
    if extracted.get("gl_occurrence_limit"):
        vendor.liability_limit = extracted["gl_occurrence_limit"]
    db.commit()

    return {"extracted": extracted, "vendor_updated": True}


# ── Portfolio Risk Dashboard ────────────────────────────────────────────────────

_portfolio_router = APIRouter(prefix="/api", tags=["portfolio"])

@_portfolio_router.get("/portfolio/risk-dashboard")
def portfolio_risk_dashboard(org_ctx=Depends(get_current_org), db: Session = Depends(get_db),
                             user=Depends(get_current_user)):
    """Multi-project risk overview for the current org."""
    org, _ = org_ctx
    projects = db.query(Project).filter(Project.org_id == org.id).all()
    today = date.today().isoformat()

    dashboard = []
    for proj in projects:
        invoices = db.query(Invoice).filter(Invoice.project_id == proj.id, Invoice.status == "processed").all()
        total_invoiced = sum(i.lender_submitted_amt or i.total_due or 0 for i in invoices)
        total_approved = sum(i.lender_approved_amt or 0 for i in invoices)
        budget = proj.total_budget or 0

        draws = db.query(Draw).filter(Draw.project_id == proj.id).all()
        open_draws = sum(1 for d in draws if d.status in ("draft", "submitted"))

        covenants = db.query(LenderCovenant).filter(LenderCovenant.project_id == proj.id).all()
        covenant_breaches = sum(1 for c in covenants if c.status == "breach")

        overdue_invoices = sum(1 for i in invoices if i.payment_status != "paid" and i.due_date and i.due_date < today)

        budget_pct = round(total_invoiced / budget * 100, 1) if budget > 0 else 0

        rag = "green"
        if covenant_breaches > 0 or budget_pct > 110:
            rag = "red"
        elif budget_pct > 90 or overdue_invoices > 5:
            rag = "amber"

        is_overdue = proj.end_date and proj.end_date < today

        dashboard.append({
            "id": proj.id,
            "name": proj.name,
            "code": proj.code,
            "province": proj.province,
            "budget": budget,
            "invoiced": round(total_invoiced, 2),
            "approved": round(total_approved, 2),
            "budget_pct": budget_pct,
            "draw_count": len(draws),
            "open_draws": open_draws,
            "covenant_breaches": covenant_breaches,
            "overdue_invoices": overdue_invoices,
            "end_date": proj.end_date,
            "is_overdue": is_overdue,
            "rag": rag,
        })

    # Sort: red first, then amber, then green
    rag_order = {"red": 0, "amber": 1, "green": 2}
    dashboard.sort(key=lambda x: (rag_order[x["rag"]], -x["budget"]))

    total_exposure = sum(p["budget"] for p in dashboard)
    red_count = sum(1 for p in dashboard if p["rag"] == "red")
    amber_count = sum(1 for p in dashboard if p["rag"] == "amber")

    return {
        "projects": dashboard,
        "summary": {
            "total_projects": len(dashboard),
            "total_budget_exposure": total_exposure,
            "red_count": red_count,
            "amber_count": amber_count,
            "green_count": len(dashboard) - red_count - amber_count,
        }
    }
