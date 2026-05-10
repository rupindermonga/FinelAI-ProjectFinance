"""
Canadian Compliance Engine + Cost-to-Complete Copilot + Vendor Pay Readiness
+ Contract-to-Invoice Matching + QuickBooks/Xero export
"""
import csv, io, json
from collections import defaultdict
from datetime import datetime as dt, timedelta
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    User, Project, Invoice, Draw, Claim, CommittedCost, ChangeOrder,
    CostCategory, InvoiceAllocation, OrgVendor, Subcontractor,
    LienWaiver, Organization, Payment, PromptPaymentLog,
)
from ..dependencies import get_current_user, get_current_org
from .audit import log as audit_log

router = APIRouter(prefix="/api/compliance", tags=["compliance"])

# ── Province rules ────────────────────────────────────────────────────────────

PROVINCE_RULES = {
    "ON": {
        "name": "Ontario",
        "holdback_pct": 10.0,
        "prompt_payment_owner_to_gc_days": 28,   # after payment cert
        "prompt_payment_gc_to_sub_days":  7,    # after GC receives payment (Ontario: 7 days)
        "lien_period_days": 60,
        "act": "Ontario Construction Act (2019)",
    },
    "BC": {
        "name": "British Columbia",
        "holdback_pct": 10.0,
        "prompt_payment_owner_to_gc_days": 28,
        "prompt_payment_gc_to_sub_days": 7,
        "lien_period_days": 45,
        "act": "BC Builders Lien Act",
    },
    "AB": {
        "name": "Alberta",
        "holdback_pct": 10.0,
        "prompt_payment_owner_to_gc_days": 28,
        "prompt_payment_gc_to_sub_days": 14,
        "lien_period_days": 45,
        "act": "Alberta Prompt Payment and Construction Lien Act (2022)",
    },
    "QC": {
        "name": "Quebec",
        "holdback_pct": 10.0,
        "prompt_payment_owner_to_gc_days": 35,
        "prompt_payment_gc_to_sub_days": 14,
        "lien_period_days": 30,
        "act": "Quebec Civil Code — Hypothèque légale",
    },
    "MB": {"name": "Manitoba", "holdback_pct": 7.5, "prompt_payment_owner_to_gc_days": 28, "prompt_payment_gc_to_sub_days": 7, "lien_period_days": 40, "act": "MB Builders' Liens Act"},
    "SK": {"name": "Saskatchewan", "holdback_pct": 10.0, "prompt_payment_owner_to_gc_days": 35, "prompt_payment_gc_to_sub_days": 14, "lien_period_days": 40, "act": "SK Builders' Lien Act"},
    "NS": {"name": "Nova Scotia", "holdback_pct": 10.0, "prompt_payment_owner_to_gc_days": 28, "prompt_payment_gc_to_sub_days": 7, "lien_period_days": 45, "act": "NS Builders' Lien Act"},
    "NB": {"name": "New Brunswick", "holdback_pct": 10.0, "prompt_payment_owner_to_gc_days": 28, "prompt_payment_gc_to_sub_days": 7, "lien_period_days": 45, "act": "NB Mechanics' Lien Act"},
}

def _rules(province: str) -> dict:
    return PROVINCE_RULES.get(province or "ON", PROVINCE_RULES["ON"])

def _deadline(from_date: str, days: int) -> str:
    try:
        return (dt.strptime(from_date, "%Y-%m-%d") + timedelta(days=days)).strftime("%Y-%m-%d")
    except Exception:
        return ""


# ══════════════════════════════════════════════════════════════════════════════
#  PROVINCE RULES REFERENCE
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/province-rules")
def get_province_rules():
    return PROVINCE_RULES


# ══════════════════════════════════════════════════════════════════════════════
#  VENDOR COMPLIANCE DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/vendors")
def vendor_compliance(
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    """Return compliance status for all org vendors: WSIB, WCB, insurance, statutory decl."""
    org, _ = org_ctx
    today = dt.utcnow().strftime("%Y-%m-%d")
    warn_date = (dt.utcnow() + timedelta(days=30)).strftime("%Y-%m-%d")

    vendors = db.query(OrgVendor).filter(OrgVendor.org_id == org.id, OrgVendor.is_active == True).all()

    result = []
    for v in vendors:
        issues = []

        def _check_expiry(label, expiry):
            if not expiry:
                issues.append({"field": label, "status": "missing", "message": f"{label} not on file"})
            elif expiry < today:
                issues.append({"field": label, "status": "expired", "message": f"{label} expired {expiry}"})
            elif expiry <= warn_date:
                issues.append({"field": label, "status": "expiring_soon", "message": f"{label} expires {expiry} (within 30 days)"})

        _check_expiry("WSIB", v.wsib_expiry)
        _check_expiry("WCB", v.wcb_expiry)
        _check_expiry("Insurance", v.insurance_expiry)

        if not v.hst_number:
            issues.append({"field": "HST/GST Number", "status": "missing", "message": "No GST/HST number on file"})
        if not v.cra_business_number:
            issues.append({"field": "CRA BN", "status": "missing", "message": "No CRA Business Number (required for T5018)"})

        severity = "ok"
        if any(i["status"] == "expired" for i in issues):
            severity = "critical"
        elif issues:
            severity = "warning"

        result.append({
            "id": v.id,
            "name": v.name,
            "vendor_code": v.vendor_code,
            "trade": v.trade,
            "province": v.province,
            "wsib_number": v.wsib_number,
            "wsib_expiry": v.wsib_expiry,
            "wcb_number": v.wcb_number,
            "wcb_expiry": v.wcb_expiry,
            "insurance_expiry": v.insurance_expiry,
            "liability_limit": v.liability_limit,
            "hst_number": v.hst_number,
            "cra_business_number": v.cra_business_number,
            "is_incorporated": v.is_incorporated,
            "statutory_declaration_date": v.statutory_declaration_date,
            "severity": severity,
            "issues": issues,
            "issue_count": len(issues),
        })

    critical = sum(1 for v in result if v["severity"] == "critical")
    warning  = sum(1 for v in result if v["severity"] == "warning")
    ok       = sum(1 for v in result if v["severity"] == "ok")

    return {
        "vendors": sorted(result, key=lambda v: {"critical":0,"warning":1,"ok":2}[v["severity"]]),
        "summary": {"total": len(result), "critical": critical, "warning": warning, "ok": ok},
    }


@router.put("/vendors/{vendor_id}/compliance")
def update_vendor_compliance(
    vendor_id: int,
    body: dict,
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update compliance fields on an org vendor."""
    org, _ = org_ctx
    v = db.query(OrgVendor).filter(OrgVendor.id == vendor_id, OrgVendor.org_id == org.id).first()
    if not v:
        raise HTTPException(404, "Vendor not found")
    fields = ["wsib_number","wsib_expiry","wcb_number","wcb_expiry","insurance_expiry",
              "liability_limit","cra_business_number","province","is_incorporated",
              "statutory_declaration_date"]
    for f in fields:
        if f in body:
            setattr(v, f, body[f])
    db.commit()
    audit_log(db, org.id, current_user, "update_vendor_compliance", "org_vendor", vendor_id,
              detail=f"Updated compliance info for vendor '{v.name}'")
    return {"message": "Updated", "id": v.id}


# ══════════════════════════════════════════════════════════════════════════════
#  T5018 SUBCONTRACTOR PAYMENT REPORT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/t5018")
def t5018_report(
    year: int = Query(default=None),
    format: str = Query(default="json"),   # json | csv
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    T5018 Statement of Contract Payments — CRA-required annual reporting
    for payments to subcontractors in construction.
    Reports total payments per vendor for the given calendar year.
    Threshold: $500+ per vendor per year triggers T5018 requirement.
    """
    org, _ = org_ctx
    if not year:
        year = dt.utcnow().year - 1  # prior year by default

    # Sum payments per vendor for the year
    year_start = f"{year}-01-01"
    year_end   = f"{year}-12-31"

    invs = db.query(Invoice).filter(
        Invoice.org_id == org.id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
        Invoice.invoice_date >= year_start,
        Invoice.invoice_date <= year_end,
    ).all()

    vendor_totals: dict = defaultdict(lambda: {
        "total_paid": 0.0, "invoice_count": 0,
        "hst": 0.0, "gst": 0.0, "vendor_info": None
    })

    for inv in invs:
        if not inv.vendor_name:
            continue
        vk = inv.vendor_name.strip()
        vendor_totals[vk]["total_paid"]    += (inv.total_due or 0)
        vendor_totals[vk]["invoice_count"] += 1
        vendor_totals[vk]["hst"]           += (inv.tax_hst or 0)
        vendor_totals[vk]["gst"]           += (inv.tax_gst or 0)

    # Enrich with vendor directory info
    org_vendors = db.query(OrgVendor).filter(OrgVendor.org_id == org.id).all()
    vendor_map = {v.name.strip(): v for v in org_vendors}

    rows = []
    for vname, data in vendor_totals.items():
        if data["total_paid"] < 500:
            continue  # CRA threshold
        ov = vendor_map.get(vname)
        rows.append({
            "vendor_name": vname,
            "cra_business_number": ov.cra_business_number if ov else None,
            "hst_number": ov.hst_number if ov else None,
            "province": ov.province if ov else None,
            "is_incorporated": ov.is_incorporated if ov else None,
            "total_payments": round(data["total_paid"], 2),
            "invoice_count": data["invoice_count"],
            "hst_collected": round(data["hst"], 2),
            "gst_collected": round(data["gst"], 2),
            "t5018_required": True,
            "missing_bn": not (ov and ov.cra_business_number),
        })

    rows.sort(key=lambda r: r["total_payments"], reverse=True)

    if format == "csv":
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=[
            "vendor_name","cra_business_number","hst_number","province","is_incorporated",
            "total_payments","invoice_count","hst_collected","gst_collected","missing_bn"
        ])
        writer.writeheader()
        writer.writerows(rows)
        output.seek(0)
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=T5018_{year}.csv"},
        )

    return {
        "year": year,
        "total_vendors": len(rows),
        "total_payments": round(sum(r["total_payments"] for r in rows), 2),
        "missing_bn_count": sum(1 for r in rows if r["missing_bn"]),
        "vendors": rows,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  PROMPT PAYMENT TRACKER
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/prompt-payment")
def prompt_payment_status(
    project_id: int = Query(...),
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Calculate prompt-payment deadlines per draw based on province rules.
    Returns overdue payments and upcoming deadlines.
    """
    org, _ = org_ctx
    proj = db.query(Project).filter(Project.id == project_id, Project.org_id == org.id).first()
    if not proj:
        raise HTTPException(404, "Project not found")

    rules = _rules(proj.province or "ON")
    today = dt.utcnow().strftime("%Y-%m-%d")
    warn_date = (dt.utcnow() + timedelta(days=7)).strftime("%Y-%m-%d")

    draws = db.query(Draw).filter(Draw.project_id == project_id).all()
    result = []

    for draw in draws:
        if not draw.submission_date:
            continue

        # Owner → GC deadline (from submission date or cert date)
        owner_gc_deadline = _deadline(draw.submission_date, rules["prompt_payment_owner_to_gc_days"])

        # GC → Sub deadline (after owner pays GC, add 7 days for ON)
        # Simplified: from submission + owner_days + sub_days
        gc_sub_deadline = _deadline(
            draw.submission_date,
            rules["prompt_payment_owner_to_gc_days"] + rules["prompt_payment_gc_to_sub_days"]
        )

        owner_gc_overdue = draw.status not in ("approved",) and owner_gc_deadline < today
        gc_sub_overdue   = draw.status not in ("approved",) and gc_sub_deadline < today

        result.append({
            "draw_id": draw.id,
            "draw_number": draw.draw_number,
            "submission_date": draw.submission_date,
            "draw_status": draw.status,
            "province": proj.province,
            "province_act": rules["act"],
            "owner_to_gc": {
                "days_allowed": rules["prompt_payment_owner_to_gc_days"],
                "deadline": owner_gc_deadline,
                "is_overdue": owner_gc_overdue,
                "days_remaining": max(0, (dt.strptime(owner_gc_deadline, "%Y-%m-%d") - dt.utcnow()).days) if owner_gc_deadline else None,
            },
            "gc_to_sub": {
                "days_allowed": rules["prompt_payment_gc_to_sub_days"],
                "deadline": gc_sub_deadline,
                "is_overdue": gc_sub_overdue,
                "days_remaining": max(0, (dt.strptime(gc_sub_deadline, "%Y-%m-%d") - dt.utcnow()).days) if gc_sub_deadline else None,
            },
            "lien_deadline": _deadline(draw.submission_date, rules["lien_period_days"]),
        })

    overdue_count = sum(1 for r in result if r["owner_to_gc"]["is_overdue"] or r["gc_to_sub"]["is_overdue"])

    return {
        "project_name": proj.name,
        "province": proj.province or "ON",
        "rules": rules,
        "draws": result,
        "overdue_count": overdue_count,
        "holdback_pct": rules["holdback_pct"],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  COST-TO-COMPLETE COPILOT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/cost-to-complete")
def cost_to_complete(
    project_id: int = Query(...),
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Forecast final project cost (Estimate at Completion).
    Uses: actual spend + open commitments + pending change orders +
    invoice velocity trend + contingency burn rate.
    """
    org, _ = org_ctx
    proj = db.query(Project).filter(Project.id == project_id, Project.org_id == org.id).first()
    if not proj:
        raise HTTPException(404, "Project not found")

    budget = proj.total_budget or 0
    contingency = proj.contingency_budget or 0
    total_available = budget + contingency

    # ── Actual spend ──────────────────────────────────────────────────────────
    invs = db.query(Invoice).filter(
        Invoice.project_id == project_id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    ).all()
    actual_spend = sum(i.total_due or 0 for i in invs)

    # ── Open commitments (uncommitted balance) ────────────────────────────────
    committed = db.query(CommittedCost).filter(
        CommittedCost.project_id == project_id,
        CommittedCost.status == "active",
    ).all()
    total_committed_value = sum(cc.contract_amount for cc in committed)
    total_invoiced_on_contracts = sum(cc.invoiced_to_date or 0 for cc in committed)
    open_commitments = max(0, total_committed_value - total_invoiced_on_contracts)

    # ── Change orders impact ──────────────────────────────────────────────────
    change_orders = db.query(ChangeOrder).filter(ChangeOrder.project_id == project_id).all()
    approved_co = sum(co.amount for co in change_orders if co.status == "approved")
    pending_co  = sum(co.amount for co in change_orders if co.status == "pending")
    rejected_co = sum(co.amount for co in change_orders if co.status == "rejected")

    # ── Invoice velocity (avg monthly spend last 3 months) ───────────────────
    from collections import defaultdict
    monthly: dict = defaultdict(float)
    for inv in invs:
        d = inv.invoice_date or (str(inv.processed_at)[:10] if inv.processed_at else None)
        if d and len(d) >= 7:
            monthly[d[:7]] += (inv.total_due or 0)

    sorted_months = sorted(monthly.keys())
    recent_3 = sorted_months[-3:] if len(sorted_months) >= 3 else sorted_months
    avg_monthly_spend = sum(monthly[m] for m in recent_3) / max(1, len(recent_3))

    # ── Category breakdown (budget vs actual) ─────────────────────────────────
    categories = db.query(CostCategory).filter(CostCategory.project_id == project_id).all()
    cat_breakdown = []
    for cat in categories:
        cat_actual = (
            db.query(func.coalesce(func.sum(InvoiceAllocation.amount), 0.0))
            .filter(InvoiceAllocation.category_id == cat.id)
            .scalar() or 0
        )
        cat_budget = cat.budget or 0
        # ETC per category = open commitments allocated to this category (approximated)
        cat_etc = max(0, cat_budget - cat_actual) if cat_budget > 0 else 0
        cat_breakdown.append({
            "category": cat.name,
            "budget": round(cat_budget, 2),
            "actual_spend": round(cat_actual, 2),
            "etc": round(cat_etc, 2),
            "eac": round(cat_actual + cat_etc, 2),
            "variance": round(cat_budget - (cat_actual + cat_etc), 2),
            "pct_complete": round(cat_actual / cat_budget * 100, 1) if cat_budget > 0 else 0,
            "is_over_budget": (cat_actual + cat_etc) > cat_budget,
        })

    # ── EAC calculations ──────────────────────────────────────────────────────
    # Method 1: actual + open commitments + pending COs
    eac_method1 = actual_spend + open_commitments + pending_co * 0.7  # 70% of pending likely to be approved

    # Method 2: if spending at current velocity, how long to finish?
    remaining_budget = budget - actual_spend
    months_to_complete = (remaining_budget / avg_monthly_spend) if avg_monthly_spend > 0 else 0
    velocity_risk = "on_track" if eac_method1 <= budget * 1.05 else ("over_budget" if eac_method1 <= budget * 1.15 else "critical")

    # ── Contingency burn ─────────────────────────────────────────────────────
    contingency_used = max(0, actual_spend - (budget - contingency)) if contingency > 0 else 0
    contingency_remaining = max(0, contingency - contingency_used)
    contingency_pct_burned = round(contingency_used / contingency * 100, 1) if contingency > 0 else 0

    # ── Holdback calculation ──────────────────────────────────────────────────
    total_holdback_retained = sum(
        (i.lender_submitted_amt or 0) * (i.holdback_pct or 0) / 100
        for i in invs
    )

    rules = _rules(proj.province or "ON")

    return {
        "project_name": proj.name,
        "province": proj.province or "ON",
        "budget": round(budget, 2),
        "contingency_budget": round(contingency, 2),
        "total_available": round(total_available, 2),
        "actual_spend": round(actual_spend, 2),
        "spend_pct": round(actual_spend / budget * 100, 1) if budget > 0 else 0,
        "open_commitments": round(open_commitments, 2),
        "change_orders": {
            "approved": round(approved_co, 2),
            "pending": round(pending_co, 2),
            "rejected": round(rejected_co, 2),
        },
        "eac": round(eac_method1, 2),
        "eac_variance": round(budget - eac_method1, 2),
        "eac_pct_of_budget": round(eac_method1 / budget * 100, 1) if budget > 0 else 0,
        "velocity_risk": velocity_risk,
        "avg_monthly_spend": round(avg_monthly_spend, 2),
        "estimated_months_remaining": round(months_to_complete, 1),
        "contingency": {
            "budget": round(contingency, 2),
            "used": round(contingency_used, 2),
            "remaining": round(contingency_remaining, 2),
            "pct_burned": contingency_pct_burned,
        },
        "holdback_retained": round(total_holdback_retained, 2),
        "holdback_pct": rules["holdback_pct"],
        "categories": sorted(cat_breakdown, key=lambda c: c.get("variance", 0)),
        "monthly_spend": [{"month": m, "amount": round(monthly[m], 2)} for m in sorted_months[-12:]],
    }


# ══════════════════════════════════════════════════════════════════════════════
#  VENDOR PAY READINESS
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/vendor-pay-readiness")
def vendor_pay_readiness(
    project_id: int = Query(...),
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Per-vendor invoice pipeline: received → validated → approved →
    holdback retained → compliance check → ready to pay → paid.
    Flags blockers for each vendor.
    """
    org, _ = org_ctx
    proj = db.query(Project).filter(Project.id == project_id, Project.org_id == org.id).first()
    if not proj:
        raise HTTPException(404, "Project not found")
    today = dt.utcnow().strftime("%Y-%m-%d")

    invs = db.query(Invoice).filter(
        Invoice.project_id == project_id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    ).all()

    # Vendor compliance data
    org_vendors = {v.name.strip().lower(): v for v in
                   db.query(OrgVendor).filter(OrgVendor.org_id == org.id).all()}
    waivers = {(w.vendor_name or "").strip().lower() for w in
               db.query(LienWaiver).filter(LienWaiver.project_id == project_id).all()}

    vendor_data: dict = defaultdict(lambda: {
        "invoices": [], "total_invoiced": 0, "total_paid": 0,
        "total_holdback": 0, "total_approved": 0,
    })

    for inv in invs:
        vk = (inv.vendor_name or "Unknown").strip()
        vkl = vk.lower()
        vendor_data[vk]["invoices"].append(inv)
        vendor_data[vk]["total_invoiced"] += (inv.total_due or 0)
        vendor_data[vk]["total_holdback"] += (inv.lender_submitted_amt or 0) * (inv.holdback_pct or 0) / 100
        vendor_data[vk]["total_approved"] += (inv.lender_approved_amt or 0)

        # Sum actual payments
        paid = db.query(func.coalesce(func.sum(Payment.amount), 0.0)).filter(
            Payment.invoice_id == inv.id
        ).scalar() or 0
        vendor_data[vk]["total_paid"] += paid

    result = []
    for vname, data in vendor_data.items():
        vkl = vname.lower()
        ov = org_vendors.get(vkl)
        invoices = data["invoices"]

        # Determine pipeline stage and blockers
        blockers = []

        # Compliance checks
        if ov:
            if ov.wsib_expiry and ov.wsib_expiry < today:
                blockers.append({"type": "compliance", "message": f"WSIB expired {ov.wsib_expiry}"})
            if ov.insurance_expiry and ov.insurance_expiry < today:
                blockers.append({"type": "compliance", "message": f"Insurance expired {ov.insurance_expiry}"})

        # Lien waiver check for large vendors
        total = data["total_invoiced"]
        threshold = max((proj.total_budget or 0) * 0.02, 5000)
        if total > threshold and vkl not in waivers:
            blockers.append({"type": "lien_waiver", "message": "No lien waiver on file"})

        # Approval check
        unapproved = [i for i in invoices if i.approval_status not in ("approved",)]
        if unapproved:
            blockers.append({"type": "approval", "message": f"{len(unapproved)} invoice(s) not approved"})

        # Unassigned to draw
        unassigned = [i for i in invoices if not i.draw_id]
        if unassigned:
            blockers.append({"type": "draw", "message": f"{len(unassigned)} invoice(s) not in a draw"})

        net_payable = data["total_approved"] - data["total_holdback"] - data["total_paid"]

        # Determine overall stage
        if data["total_paid"] >= data["total_approved"] > 0:
            stage = "paid"
        elif blockers:
            stage = "blocked"
        elif data["total_approved"] > 0 and not blockers:
            stage = "ready_to_pay"
        elif data["total_approved"] > 0:
            stage = "approved"
        elif any(i.lender_submitted_amt for i in invoices):
            stage = "submitted_to_lender"
        else:
            stage = "received"

        result.append({
            "vendor": vname,
            "stage": stage,
            "total_invoiced": round(data["total_invoiced"], 2),
            "total_approved": round(data["total_approved"], 2),
            "total_holdback": round(data["total_holdback"], 2),
            "total_paid": round(data["total_paid"], 2),
            "net_payable": round(max(0, net_payable), 2),
            "invoice_count": len(invoices),
            "blockers": blockers,
            "has_lien_waiver": vkl in waivers,
            "wsib_expiry": ov.wsib_expiry if ov else None,
            "insurance_expiry": ov.insurance_expiry if ov else None,
        })

    result.sort(key=lambda v: {"blocked":0,"received":1,"submitted_to_lender":2,
                                "approved":3,"ready_to_pay":4,"paid":5}[v["stage"]])

    return {
        "project_name": proj.name,
        "vendors": result,
        "summary": {
            "total_vendors": len(result),
            "blocked": sum(1 for v in result if v["stage"] == "blocked"),
            "ready_to_pay": sum(1 for v in result if v["stage"] == "ready_to_pay"),
            "paid": sum(1 for v in result if v["stage"] == "paid"),
            "total_net_payable": round(sum(v["net_payable"] for v in result), 2),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  CONTRACT-TO-INVOICE MATCHING
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/contract-matching")
def contract_invoice_matching(
    project_id: int = Query(...),
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    AI-assisted contract-to-invoice matching.
    Matches invoices to committed contracts/POs by vendor name.
    Flags unmatched invoices, over-billed contracts, and invoices
    without a matching contract.
    """
    org, _ = org_ctx
    proj = db.query(Project).filter(Project.id == project_id, Project.org_id == org.id).first()
    if not proj:
        raise HTTPException(404, "Project not found")

    invs = db.query(Invoice).filter(
        Invoice.project_id == project_id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    ).all()

    committed = db.query(CommittedCost).filter(
        CommittedCost.project_id == project_id,
        CommittedCost.status.in_(["active","complete"]),
    ).all()

    change_orders = db.query(ChangeOrder).filter(
        ChangeOrder.project_id == project_id,
        ChangeOrder.status == "approved",
    ).all()

    # Build vendor invoice totals
    vendor_inv: dict = defaultdict(list)
    for inv in invs:
        if inv.vendor_name:
            vendor_inv[inv.vendor_name.strip().lower()].append(inv)

    # Match contracts to invoices (fuzzy vendor name match)
    def _match_score(a: str, b: str) -> float:
        a, b = a.lower().strip(), b.lower().strip()
        if a == b:
            return 1.0
        if a in b or b in a:
            return 0.85
        # Word overlap
        wa, wb = set(a.split()), set(b.split())
        if not wa or not wb:
            return 0.0
        overlap = len(wa & wb) / max(len(wa), len(wb))
        return overlap

    contract_matches = []
    for cc in committed:
        vname = cc.vendor or ""
        best_match = None
        best_score = 0.6  # threshold

        for inv_vendor_key in vendor_inv:
            score = _match_score(vname, inv_vendor_key)
            if score > best_score:
                best_score = score
                best_match = inv_vendor_key

        matched_invs = vendor_inv.get(best_match, []) if best_match else []
        invoiced_total = sum(i.total_due or 0 for i in matched_invs)

        # Add relevant change orders
        co_total = sum(co.amount for co in change_orders
                       if _match_score(vname, co.description or "") > 0.5)
        adjusted_contract = cc.contract_amount + co_total

        contract_matches.append({
            "contract_id": cc.id,
            "vendor": cc.vendor,
            "contract_amount": round(cc.contract_amount, 2),
            "co_additions": round(co_total, 2),
            "adjusted_contract": round(adjusted_contract, 2),
            "invoiced_to_date": round(invoiced_total, 2),
            "remaining": round(adjusted_contract - invoiced_total, 2),
            "pct_invoiced": round(invoiced_total / adjusted_contract * 100, 1) if adjusted_contract > 0 else 0,
            "matched_vendor_key": best_match,
            "match_confidence": round(best_score, 2),
            "matched_invoice_count": len(matched_invs),
            "is_over_billed": invoiced_total > adjusted_contract * 1.02,
            "status": cc.status,
        })

    # Unmatched invoices (no contract)
    matched_vendor_keys = {m["matched_vendor_key"] for m in contract_matches if m["matched_vendor_key"]}
    unmatched_inv = []
    for vk, invs_list in vendor_inv.items():
        if vk not in matched_vendor_keys:
            total = sum(i.total_due or 0 for i in invs_list)
            unmatched_inv.append({
                "vendor": invs_list[0].vendor_name if invs_list else vk,
                "invoice_count": len(invs_list),
                "total_invoiced": round(total, 2),
                "risk": "no_contract",
                "message": "Invoices received but no matching committed contract/PO found.",
            })

    return {
        "project_name": proj.name,
        "contract_matches": sorted(contract_matches, key=lambda c: c["is_over_billed"], reverse=True),
        "unmatched_invoices": unmatched_inv,
        "summary": {
            "total_contracts": len(committed),
            "over_billed": sum(1 for c in contract_matches if c["is_over_billed"]),
            "unmatched_vendors": len(unmatched_inv),
            "total_committed": round(sum(cc.contract_amount for cc in committed), 2),
            "total_invoiced": round(sum(i.total_due or 0 for i in invs), 2),
        },
    }


# ══════════════════════════════════════════════════════════════════════════════
#  QUICKBOOKS / XERO EXPORT
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/export/quickbooks")
def export_quickbooks(
    project_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export invoices in QuickBooks IIF-compatible CSV format.
    Maps vendor, amount, account, tax, date for import into QuickBooks Desktop/Online.
    """
    org, _ = org_ctx
    q = db.query(Invoice).filter(
        Invoice.org_id == org.id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    )
    if project_id:
        q = q.filter(Invoice.project_id == project_id)
    if start_date:
        q = q.filter(Invoice.invoice_date >= start_date)
    if end_date:
        q = q.filter(Invoice.invoice_date <= end_date)
    invs = q.order_by(Invoice.invoice_date).all()

    output = io.StringIO()
    writer = csv.writer(output)
    # QuickBooks Online import format
    writer.writerow([
        "Date", "Vendor", "Invoice Number", "Account", "Amount",
        "Tax Amount", "Tax Code", "Description", "Reference",
        "Currency", "Project"
    ])

    for inv in invs:
        proj = db.query(Project).filter(Project.id == inv.project_id).first() if inv.project_id else None
        tax = (inv.tax_hst or inv.tax_gst or inv.tax_pst or inv.tax_total or 0)
        tax_code = "HST" if inv.tax_hst else ("GST" if inv.tax_gst else ("PST" if inv.tax_pst else ""))
        writer.writerow([
            inv.invoice_date or "",
            inv.vendor_name or "",
            inv.invoice_number or "",
            "Construction Costs",
            round(inv.subtotal or inv.total_due or 0, 2),
            round(tax, 2),
            tax_code,
            f"Invoice from {inv.vendor_name or ''}",
            str(inv.id),
            inv.currency or "CAD",
            proj.name if proj else "",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=QuickBooks_Import.csv"},
    )


@router.get("/export/xero")
def export_xero(
    project_id: Optional[int] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Export invoices in Xero Bills CSV import format.
    Compatible with Xero's standard bill import template.
    """
    org, _ = org_ctx
    q = db.query(Invoice).filter(
        Invoice.org_id == org.id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    )
    if project_id:
        q = q.filter(Invoice.project_id == project_id)
    if start_date:
        q = q.filter(Invoice.invoice_date >= start_date)
    if end_date:
        q = q.filter(Invoice.invoice_date <= end_date)
    invs = q.order_by(Invoice.invoice_date).all()

    output = io.StringIO()
    writer = csv.writer(output)
    # Xero Bills import format
    writer.writerow([
        "*ContactName", "*InvoiceNumber", "*InvoiceDate", "*DueDate",
        "Description", "*UnitAmount", "*AccountCode", "*TaxType",
        "TrackingName1", "TrackingOption1", "Currency"
    ])

    for inv in invs:
        proj = db.query(Project).filter(Project.id == inv.project_id).first() if inv.project_id else None
        # Determine tax type for Xero
        if inv.tax_hst:
            tax_type = "HST on Expenses"
        elif inv.tax_gst:
            tax_type = "GST on Expenses"
        elif inv.tax_pst:
            tax_type = "PST"
        else:
            tax_type = "Tax Exempt"

        due_date = inv.due_date or inv.invoice_date or ""
        writer.writerow([
            inv.vendor_name or "Unknown Vendor",
            inv.invoice_number or f"INV-{inv.id}",
            inv.invoice_date or "",
            due_date,
            f"Construction invoice - {proj.name if proj else 'Project'}",
            round(inv.subtotal or inv.total_due or 0, 2),
            "200",   # Xero account code for purchases
            tax_type,
            "Project" if proj else "",
            proj.name if proj else "",
            inv.currency or "CAD",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=Xero_Bills_Import.csv"},
    )
