"""
Phase 10 — Lender Advanced Features
- QS / Inspector structured portal + Gemini PDF parsing
- Mezzanine / second-mortgage tranche tracking
- CMHC take-out / permanent financing conversion
- Loan pre-funding closing document checklist (seed: 40 standard items)
"""
from __future__ import annotations

import os
import json
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, require_project_access, FINANCE_READ_ROLES, call_gemini_api
from ..models import (
    QSReport, QSTradeItem,
    MezzTranche, TakeoutConversion,
    LoanClosingChecklistItem,
    User,
)

router = APIRouter(prefix="/api", tags=["lender-advanced"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── QS / Inspector Reports ───────────────────────────────────────────────────

@router.get("/project/{project_id}/qs-reports")
def list_qs_reports(project_id: int, db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    rows = (db.query(QSReport)
            .filter(QSReport.project_id == project_id, QSReport.org_id == current_user.org_id)
            .order_by(QSReport.report_date.desc()).all())
    out = []
    for r in rows:
        d = r.__dict__.copy()
        d.pop("_sa_instance_state", None)
        d["trade_items"] = [
            {k: v for k, v in t.__dict__.items() if k != "_sa_instance_state"}
            for t in r.trade_items
        ]
        out.append(d)
    return out


@router.post("/project/{project_id}/qs-reports")
def create_qs_report(project_id: int, body: dict,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    trade_items = body.pop("trade_items", [])
    report = QSReport(
        org_id=current_user.org_id, project_id=project_id,
        created_by=current_user.id,
        **{k: v for k, v in body.items() if hasattr(QSReport, k)}
    )
    db.add(report)
    db.flush()
    for t in trade_items:
        db.add(QSTradeItem(
            report_id=report.id,
            org_id=current_user.org_id,
            project_id=project_id,
            **{k: v for k, v in t.items() if hasattr(QSTradeItem, k)}
        ))
    db.commit()
    db.refresh(report)
    return {"id": report.id, "msg": "QS report created"}


@router.put("/project/{project_id}/qs-reports/{report_id}")
def update_qs_report(project_id: int, report_id: int, body: dict,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    report = db.query(QSReport).filter(QSReport.id == report_id,
                                       QSReport.org_id == current_user.org_id).first()
    if not report:
        raise HTTPException(404, "QS report not found")
    trade_items = body.pop("trade_items", None)
    for k, v in body.items():
        if hasattr(report, k):
            setattr(report, k, v)
    if trade_items is not None:
        for t in report.trade_items:
            db.delete(t)
        for t in trade_items:
            db.add(QSTradeItem(
                report_id=report.id, org_id=current_user.org_id,
                project_id=project_id,
                **{k: v for k, v in t.items() if hasattr(QSTradeItem, k)}
            ))
    db.commit()
    return {"msg": "updated"}


@router.delete("/project/{project_id}/qs-reports/{report_id}")
def delete_qs_report(project_id: int, report_id: int,
                     db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    report = db.query(QSReport).filter(QSReport.id == report_id,
                                       QSReport.org_id == current_user.org_id).first()
    if not report:
        raise HTTPException(404, "QS report not found")
    db.delete(report)
    db.commit()
    return {"msg": "deleted"}


@router.post("/project/{project_id}/qs-reports/ai-parse")
async def ai_parse_qs_report(
    project_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a QS PDF report; Gemini extracts structured data."""
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)

    import base64
    content = await file.read()
    b64 = base64.b64encode(content).decode()

    prompt = """You are analyzing a Quantity Surveyor (QS) / Project Monitor report for a Canadian construction loan draw.
Extract the following structured data from the PDF and return valid JSON only:
{
  "qs_firm": "firm name or null",
  "report_date": "YYYY-MM-DD or null",
  "overall_pct_complete": numeric or null,
  "cost_to_complete": numeric or null,
  "contingency_remaining": numeric or null,
  "schedule_status": "on_track|delayed|at_risk",
  "schedule_delay_weeks": integer or null,
  "deficiency_count": integer,
  "deficiency_notes": "text or null",
  "recommendation": "approve|conditional|decline",
  "summary": "2-3 sentence executive summary",
  "trade_items": [
    {
      "trade_name": "e.g. Concrete",
      "csi_division": "e.g. 03 or null",
      "budget_amount": numeric or null,
      "cost_to_date": numeric or null,
      "cost_to_complete": numeric or null,
      "pct_complete": numeric or null,
      "status": "on_track|delayed|at_risk|complete",
      "deficiencies": "text or null"
    }
  ]
}
Return ONLY valid JSON with no markdown fences."""

    try:
        result = await call_gemini_api(
            {
                "contents": [{
                    "parts": [
                        {"text": prompt},
                        {"inline_data": {"mime_type": "application/pdf", "data": b64}}
                    ]
                }],
                "generationConfig": {"temperature": 0.1},
            },
            timeout=60,
        )
        raw = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        parsed = json.loads(raw)
    except Exception as e:
        raise HTTPException(502, f"AI parsing failed: {e}")

    return parsed


# ─── Mezz / Tranche Tracking ──────────────────────────────────────────────────

@router.get("/project/{project_id}/mezz-tranches")
def list_mezz_tranches(project_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    rows = (db.query(MezzTranche)
            .filter(MezzTranche.project_id == project_id,
                    MezzTranche.org_id == current_user.org_id)
            .order_by(MezzTranche.priority_rank).all())
    total_commitment = sum(r.commitment_amount or 0 for r in rows)
    total_drawn = sum(r.drawn_amount or 0 for r in rows)
    return {
        "tranches": [{k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"} for r in rows],
        "summary": {
            "total_commitment": total_commitment,
            "total_drawn": total_drawn,
            "total_available": total_commitment - total_drawn,
        }
    }


@router.post("/project/{project_id}/mezz-tranches")
def create_mezz_tranche(project_id: int, body: dict,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    tranche = MezzTranche(
        org_id=current_user.org_id, project_id=project_id,
        created_by=current_user.id,
        **{k: v for k, v in body.items() if hasattr(MezzTranche, k)}
    )
    db.add(tranche)
    db.commit()
    db.refresh(tranche)
    return {"id": tranche.id, "msg": "tranche created"}


@router.put("/project/{project_id}/mezz-tranches/{tranche_id}")
def update_mezz_tranche(project_id: int, tranche_id: int, body: dict,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    tranche = db.query(MezzTranche).filter(MezzTranche.id == tranche_id,
                                           MezzTranche.org_id == current_user.org_id).first()
    if not tranche:
        raise HTTPException(404, "Tranche not found")
    for k, v in body.items():
        if hasattr(tranche, k):
            setattr(tranche, k, v)
    db.commit()
    return {"msg": "updated"}


@router.delete("/project/{project_id}/mezz-tranches/{tranche_id}")
def delete_mezz_tranche(project_id: int, tranche_id: int,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    tranche = db.query(MezzTranche).filter(MezzTranche.id == tranche_id,
                                           MezzTranche.org_id == current_user.org_id).first()
    if not tranche:
        raise HTTPException(404)
    db.delete(tranche)
    db.commit()
    return {"msg": "deleted"}


# ─── CMHC Take-out / Perm Conversion ─────────────────────────────────────────

@router.get("/project/{project_id}/takeout-conversion")
def get_takeout_conversion(project_id: int, db: Session = Depends(get_db),
                           current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    row = db.query(TakeoutConversion).filter(
        TakeoutConversion.project_id == project_id,
        TakeoutConversion.org_id == current_user.org_id
    ).first()
    if not row:
        return None
    return {k: v for k, v in row.__dict__.items() if k != "_sa_instance_state"}


@router.post("/project/{project_id}/takeout-conversion")
def upsert_takeout_conversion(project_id: int, body: dict,
                              db: Session = Depends(get_db),
                              current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    row = db.query(TakeoutConversion).filter(
        TakeoutConversion.project_id == project_id,
        TakeoutConversion.org_id == current_user.org_id
    ).first()
    if row:
        for k, v in body.items():
            if hasattr(row, k):
                setattr(row, k, v)
    else:
        row = TakeoutConversion(
            org_id=current_user.org_id, project_id=project_id,
            created_by=current_user.id,
            **{k: v for k, v in body.items() if hasattr(TakeoutConversion, k)}
        )
        db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "msg": "saved"}


# ─── Loan Pre-Funding Closing Checklist ───────────────────────────────────────

_CLOSING_CHECKLIST_SEED = [
    # Zoning & Land
    ("zoning", "Zoning Confirmation Letter", "Municipal zoning confirmation letter"),
    ("zoning", "Zoning Certificate / Compliance Report", "Certificate of zoning compliance"),
    ("zoning", "Site Plan Approval", "Approved site plan from municipality"),
    ("zoning", "Consent / Minor Variance", "Consent or minor variance (if applicable)"),
    # Environmental
    ("environmental", "Phase I Environmental Site Assessment", "Phase I ESA (max 18 months old)"),
    ("environmental", "Phase II ESA", "Phase II ESA (if required from Phase I)"),
    ("environmental", "Record of Site Condition (RSC)", "RSC filed on Ministry registry (ON)"),
    ("environmental", "Geotechnical Report", "Geotech / soil investigation report"),
    # Title & Legal
    ("title", "Title Search / Certificate of Title", "Clean title search or solicitor's certificate"),
    ("title", "ALTA / AOLS Survey", "Land survey or legal description"),
    ("title", "Title Insurance Commitment", "Lender's title insurance policy commitment"),
    ("title", "Solicitor's Opinion Letter", "Borrower's solicitor opinion on enforceability"),
    ("title", "Partnership / SPV Documentation", "Operating agreement, articles, SPV structure"),
    ("title", "Personal Guarantees", "Signed personal guarantees from principals"),
    # Construction
    ("construction", "Building Permit (Main)", "Primary building permit issued"),
    ("construction", "Fixed-Price GC Contract (CCDC 2)", "Executed fixed-price GC contract"),
    ("construction", "Construction Schedule", "Baseline CPM schedule"),
    ("construction", "Cost Breakdown / Budget", "Full project budget by CSI division"),
    ("construction", "GC Qualification Statement", "GC financial statements and references"),
    ("construction", "Subcontract Summary", "Summary of major subcontracts"),
    # Insurance & Bonds
    ("insurance", "All-Risk Course of Construction Insurance", "Builder's risk / all-risk COC policy"),
    ("insurance", "General Liability Certificate (GC)", "GC CGL ≥ $5M per occurrence"),
    ("insurance", "Payment & Performance Bond (GC)", "50% P&P bond from GC surety"),
    ("insurance", "WSIB / WCB Clearance Certificate", "Current WSIB clearance for GC"),
    # Financial
    ("financial", "Borrower Financial Statements", "3 years CPA-reviewed or audited financials"),
    ("financial", "Project Proforma", "Full project financial projection"),
    ("financial", "Equity Injection Confirmation", "Bank confirmation of equity deposited"),
    ("financial", "Sources & Uses Statement", "Executed sources and uses of funds"),
    # Pre-Sales / Pre-Leasing (for applicable projects)
    ("presales", "Pre-Sales Summary", "Executed purchase agreements meeting threshold"),
    ("presales", "Pre-Lease Summary", "Executed lease agreements meeting threshold"),
    # CMHC (if applicable)
    ("cmhc", "CMHC Commitment Letter", "CMHC insurance commitment letter"),
    ("cmhc", "CMHC Approved Plans & Specs", "Plans approved by CMHC technical reviewer"),
    # Appraisal
    ("appraisal", "As-Is Appraisal", "Appraisal of land as-is"),
    ("appraisal", "As-Complete Appraisal", "Appraisal of completed project value"),
    # Regulatory
    ("regulatory", "Notice of Project (MOL/OH&S)", "Filed with provincial OHS authority"),
    ("regulatory", "ESA / Electrical Permit", "Electrical Safety Authority permit (ON)"),
    # Syndication (if applicable)
    ("syndication", "Intercreditor Agreement", "Signed intercreditor / priority agreement"),
    ("syndication", "Participation Agreements", "Executed participation agreements (all lenders)"),
    # Miscellaneous
    ("misc", "Borrower's Certificate", "Borrower's representation and warranty certificate"),
    ("misc", "Drawdown Request Procedures", "Agreed drawdown request and inspector appointment"),
]


@router.get("/project/{project_id}/loan-closing-checklist")
def list_loan_closing_checklist(project_id: int, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    rows = (db.query(LoanClosingChecklistItem)
            .filter(LoanClosingChecklistItem.project_id == project_id,
                    LoanClosingChecklistItem.org_id == current_user.org_id)
            .order_by(LoanClosingChecklistItem.category, LoanClosingChecklistItem.display_order)
            .all())
    items = [{k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"} for r in rows]
    total = len(items)
    received = sum(1 for i in items if i["status"] == "received")
    waived = sum(1 for i in items if i["status"] == "waived")
    outstanding = sum(1 for i in items if i["status"] == "outstanding")
    return {"items": items, "summary": {"total": total, "received": received, "waived": waived, "outstanding": outstanding}}


@router.post("/project/{project_id}/loan-closing-checklist/seed")
def seed_loan_closing_checklist(project_id: int, db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    existing = db.query(LoanClosingChecklistItem).filter(
        LoanClosingChecklistItem.project_id == project_id,
        LoanClosingChecklistItem.org_id == current_user.org_id
    ).count()
    if existing:
        raise HTTPException(400, "Checklist already seeded for this project")
    for i, (cat, name, desc) in enumerate(_CLOSING_CHECKLIST_SEED):
        db.add(LoanClosingChecklistItem(
            org_id=current_user.org_id, project_id=project_id,
            category=cat, item_name=name, description=desc,
            display_order=i * 10, created_by=current_user.id
        ))
    db.commit()
    return {"msg": f"Seeded {len(_CLOSING_CHECKLIST_SEED)} checklist items"}


@router.post("/project/{project_id}/loan-closing-checklist")
def create_loan_closing_item(project_id: int, body: dict,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    item = LoanClosingChecklistItem(
        org_id=current_user.org_id, project_id=project_id,
        created_by=current_user.id,
        **{k: v for k, v in body.items() if hasattr(LoanClosingChecklistItem, k)}
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    return {"id": item.id, "msg": "created"}


@router.put("/project/{project_id}/loan-closing-checklist/{item_id}")
def update_loan_closing_item(project_id: int, item_id: int, body: dict,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    item = db.query(LoanClosingChecklistItem).filter(
        LoanClosingChecklistItem.id == item_id,
        LoanClosingChecklistItem.org_id == current_user.org_id
    ).first()
    if not item:
        raise HTTPException(404)
    for k, v in body.items():
        if hasattr(item, k):
            setattr(item, k, v)
    db.commit()
    return {"msg": "updated"}


@router.delete("/project/{project_id}/loan-closing-checklist/{item_id}")
def delete_loan_closing_item(project_id: int, item_id: int,
                             db: Session = Depends(get_db),
                             current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    item = db.query(LoanClosingChecklistItem).filter(
        LoanClosingChecklistItem.id == item_id,
        LoanClosingChecklistItem.org_id == current_user.org_id
    ).first()
    if not item:
        raise HTTPException(404)
    db.delete(item)
    db.commit()
    return {"msg": "deleted"}
