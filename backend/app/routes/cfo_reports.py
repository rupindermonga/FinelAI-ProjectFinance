"""CFO Reporting Suite — Backlog, Margin Fade, Retainage Aging, CO Exposure,
AP Aging, Draw SLA, Committed vs Buyout, Vendor Risk, AI Lender Memo."""
import os, json
from datetime import datetime, date, timedelta
from collections import defaultdict
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user, get_current_org, FINANCE_READ_ROLES, call_gemini_api
from ..models import (
    Project, Invoice, Draw, ChangeOrder, CommittedCost, CostCategory,
    InvoiceAllocation, OrgVendor, LenderCovenant, Payment,
)

router = APIRouter(prefix="/api/reports", tags=["cfo-reports"])


def _get_org(org_ctx, db):
    org, mem = org_ctx
    if mem.role not in FINANCE_READ_ROLES:
        raise HTTPException(403)
    return org


# ── Backlog Report ─────────────────────────────────────────────────────────────

@router.get("/backlog")
def backlog_report(org_ctx=Depends(get_current_org), db: Session = Depends(get_db)):
    """Future contracted revenue not yet invoiced — capacity planning view."""
    org = _get_org(org_ctx, db)
    projects = db.query(Project).filter(Project.org_id == org.id).all()
    rows = []
    total_contract = 0; total_invoiced = 0; total_backlog = 0
    for proj in projects:
        cos = db.query(ChangeOrder).filter(ChangeOrder.project_id == proj.id, ChangeOrder.status == "approved").all()
        revised = (proj.total_budget or 0) + sum(c.amount for c in cos)
        invoiced = sum(i.lender_submitted_amt or i.total_due or 0
                       for i in db.query(Invoice).filter(Invoice.project_id == proj.id, Invoice.status == "processed").all())
        backlog = max(0, revised - invoiced)
        pct = round(invoiced / revised * 100, 1) if revised > 0 else 0
        rows.append({
            "project_id": proj.id, "project_name": proj.name, "code": proj.code,
            "province": proj.province, "end_date": proj.end_date,
            "revised_contract": revised, "invoiced": invoiced,
            "backlog": backlog, "pct_complete": pct,
            "is_overdue": proj.end_date and proj.end_date < date.today().isoformat(),
        })
        total_contract += revised; total_invoiced += invoiced; total_backlog += backlog
    rows.sort(key=lambda x: -x["backlog"])
    return {
        "projects": rows,
        "summary": {
            "total_contract": total_contract, "total_invoiced": total_invoiced,
            "total_backlog": total_backlog,
            "backlog_pct": round(total_backlog / total_contract * 100, 1) if total_contract else 0,
            "project_count": len(rows),
        }
    }


# ── Margin Fade / Gain ─────────────────────────────────────────────────────────

@router.get("/margin-fade")
def margin_fade(org_ctx=Depends(get_current_org), db: Session = Depends(get_db)):
    """Original budget vs revised vs actual — shows where margin is being lost/gained."""
    org = _get_org(org_ctx, db)
    projects = db.query(Project).filter(Project.org_id == org.id).all()
    rows = []
    for proj in projects:
        original = proj.total_budget or 0
        approved_cos = db.query(ChangeOrder).filter(
            ChangeOrder.project_id == proj.id, ChangeOrder.status == "approved").all()
        pending_cos = db.query(ChangeOrder).filter(
            ChangeOrder.project_id == proj.id, ChangeOrder.status == "pending").all()
        co_approved = sum(c.amount for c in approved_cos)
        co_pending = sum(c.amount for c in pending_cos)
        revised = original + co_approved
        actual_invoiced = sum(i.lender_submitted_amt or i.total_due or 0
                              for i in db.query(Invoice).filter(
                                  Invoice.project_id == proj.id, Invoice.status == "processed").all())
        committed = sum(c.contract_amount for c in db.query(CommittedCost).filter(
            CommittedCost.project_id == proj.id, CommittedCost.status == "active").all())
        eac = actual_invoiced + committed  # Estimate at Completion
        margin_fade = original - eac
        rows.append({
            "project_id": proj.id, "project_name": proj.name,
            "original_budget": original, "co_approved": co_approved,
            "co_pending": co_pending, "revised_budget": revised,
            "actual_invoiced": actual_invoiced, "committed": committed,
            "eac": eac, "margin_fade": round(margin_fade, 2),
            "margin_fade_pct": round(margin_fade / original * 100, 1) if original else 0,
        })
    rows.sort(key=lambda x: x["margin_fade"])  # most overrun first
    return {"projects": rows}


# ── Retainage / Holdback Aging ─────────────────────────────────────────────────

@router.get("/retainage-aging")
def retainage_aging(org_ctx=Depends(get_current_org), db: Session = Depends(get_db),
                    project_id: int = None):
    """Holdback aging by vendor — how long has each holdback been held?"""
    org = _get_org(org_ctx, db)
    q = db.query(Invoice).filter(
        Invoice.org_id == org.id, Invoice.status == "processed",
        Invoice.holdback_released == False,
        Invoice.lender_approved_amt != None,
    )
    if project_id: q = q.filter(Invoice.project_id == project_id)
    invoices = q.all()
    today = date.today()
    buckets = defaultdict(lambda: {"current": 0, "30_60": 0, "60_90": 0, "90_plus": 0, "total": 0, "invoices": []})
    for inv in invoices:
        holdback = (inv.lender_approved_amt or 0) * (inv.holdback_pct or 10) / 100
        if holdback <= 0: continue
        vendor = inv.vendor_name or "Unknown"
        inv_date = inv.invoice_date or inv.processed_at.strftime("%Y-%m-%d") if inv.processed_at else None
        if inv_date:
            age_days = (today - datetime.strptime(inv_date, "%Y-%m-%d").date()).days
        else:
            age_days = 0
        bucket = "current" if age_days < 30 else ("30_60" if age_days < 60 else ("60_90" if age_days < 90 else "90_plus"))
        buckets[vendor][bucket] += holdback
        buckets[vendor]["total"] += holdback
        buckets[vendor]["invoices"].append({"id": inv.id, "invoice_number": inv.invoice_number, "holdback": round(holdback, 2), "age_days": age_days})
    rows = [{"vendor": k, **{kk: round(v, 2) if isinstance(v, float) else v for kk, v in data.items()}} for k, data in buckets.items()]
    rows.sort(key=lambda x: -x["total"])
    return {
        "rows": rows,
        "summary": {
            "total_holdback": round(sum(r["total"] for r in rows), 2),
            "current": round(sum(r["current"] for r in rows), 2),
            "30_60": round(sum(r["30_60"] for r in rows), 2),
            "60_90": round(sum(r["60_90"] for r in rows), 2),
            "90_plus": round(sum(r["90_plus"] for r in rows), 2),
            "vendor_count": len(rows),
        }
    }


# ── Change Order Exposure Log ──────────────────────────────────────────────────

@router.get("/co-exposure")
def co_exposure(org_ctx=Depends(get_current_org), db: Session = Depends(get_db),
                project_id: int = None):
    """Full CO register — approved, pending, rejected, disputed."""
    org = _get_org(org_ctx, db)
    projects = {p.id: p for p in db.query(Project).filter(Project.org_id == org.id).all()}
    q = db.query(ChangeOrder).filter(ChangeOrder.project_id.in_(projects.keys()))
    if project_id: q = q.filter(ChangeOrder.project_id == project_id)
    cos = q.order_by(ChangeOrder.project_id, ChangeOrder.status, ChangeOrder.date.desc()).all()
    rows = [{"id": c.id, "co_number": c.co_number, "project_id": c.project_id,
             "project_name": projects.get(c.project_id, type("", (), {"name": ""})()).name,
             "description": c.description, "amount": c.amount, "status": c.status,
             "issued_by": c.issued_by, "date": c.date, "notes": c.notes} for c in cos]
    by_status = defaultdict(float)
    for c in cos: by_status[c.status] += c.amount
    return {
        "change_orders": rows,
        "summary": {s: round(v, 2) for s, v in by_status.items()},
        "total_exposure": round(sum(c.amount for c in cos if c.status == "pending"), 2),
        "total_approved": round(by_status.get("approved", 0), 2),
        "total_rejected": round(by_status.get("rejected", 0), 2),
    }


# ── AP Aging ───────────────────────────────────────────────────────────────────

@router.get("/ap-aging")
def ap_aging(org_ctx=Depends(get_current_org), db: Session = Depends(get_db),
             project_id: int = None):
    """AP aging — unpaid invoices by vendor and age bucket."""
    org = _get_org(org_ctx, db)
    today = date.today().isoformat()
    q = db.query(Invoice).filter(
        Invoice.org_id == org.id, Invoice.status == "processed",
        Invoice.payment_status != "paid",
    )
    if project_id: q = q.filter(Invoice.project_id == project_id)
    invoices = q.all()
    buckets = defaultdict(lambda: {"current": 0, "1_30": 0, "31_60": 0, "61_90": 0, "90_plus": 0, "total": 0})
    for inv in invoices:
        amt = (inv.lender_approved_amt or inv.total_due or 0) - (inv.amount_paid or 0)
        if amt <= 0: continue
        vendor = inv.vendor_name or "Unknown"
        due = inv.due_date
        if due:
            overdue_days = (date.today() - datetime.strptime(due, "%Y-%m-%d").date()).days
        else:
            overdue_days = 0
        if overdue_days <= 0: bucket = "current"
        elif overdue_days <= 30: bucket = "1_30"
        elif overdue_days <= 60: bucket = "31_60"
        elif overdue_days <= 90: bucket = "61_90"
        else: bucket = "90_plus"
        buckets[vendor][bucket] += amt
        buckets[vendor]["total"] += amt
    rows = [{"vendor": k, **{kk: round(v, 2) for kk, v in data.items()}} for k, data in buckets.items()]
    rows.sort(key=lambda x: -x["total"])
    overdue = sum(r["1_30"]+r["31_60"]+r["61_90"]+r["90_plus"] for r in rows)
    return {
        "rows": rows,
        "summary": {
            "total_ap": round(sum(r["total"] for r in rows), 2),
            "overdue": round(overdue, 2),
            "current": round(sum(r["current"] for r in rows), 2),
            "1_30": round(sum(r["1_30"] for r in rows), 2),
            "31_60": round(sum(r["31_60"] for r in rows), 2),
            "61_90": round(sum(r["61_90"] for r in rows), 2),
            "90_plus": round(sum(r["90_plus"] for r in rows), 2),
        }
    }


# ── Draw SLA Dashboard ─────────────────────────────────────────────────────────

@router.get("/draw-sla")
def draw_sla(org_ctx=Depends(get_current_org), db: Session = Depends(get_db)):
    """Submission-to-approval timing for all draws — lender performance tracking."""
    org = _get_org(org_ctx, db)
    projects = {p.id: p for p in db.query(Project).filter(Project.org_id == org.id).all()}
    draws = db.query(Draw).filter(Draw.project_id.in_(projects.keys())).order_by(Draw.submission_date.desc()).all()
    rows = []
    total_days = 0; count = 0
    for d in draws:
        proj = projects.get(d.project_id)
        invoices = db.query(Invoice).filter(Invoice.draw_id == d.id).all()
        submitted = sum(i.lender_submitted_amt or i.total_due or 0 for i in invoices)
        approved = sum(i.lender_approved_amt or 0 for i in invoices)
        # For SLA tracking, estimate approval timing from status
        days_open = None
        if d.submission_date and d.status == "approved":
            # Approximate — real system would track approval_date
            days_open = 28  # placeholder
        elif d.submission_date and d.status in ("submitted", "draft"):
            try:
                days_open = (date.today() - datetime.strptime(d.submission_date, "%Y-%m-%d").date()).days
            except Exception:
                days_open = None
        if days_open is not None and d.status == "approved":
            total_days += days_open; count += 1
        rows.append({
            "draw_id": d.id, "draw_number": d.draw_number,
            "project_name": proj.name if proj else "",
            "project_id": d.project_id,
            "submission_date": d.submission_date, "status": d.status,
            "submitted_amount": round(submitted, 2), "approved_amount": round(approved, 2),
            "days_open": days_open,
            "sla_flag": "over_30" if days_open and days_open > 30 else ("over_14" if days_open and days_open > 14 else "ok"),
        })
    avg_days = round(total_days / count, 1) if count else None
    return {
        "draws": rows,
        "summary": {
            "total_draws": len(draws),
            "approved": sum(1 for d in draws if d.status == "approved"),
            "pending": sum(1 for d in draws if d.status in ("draft","submitted")),
            "avg_approval_days": avg_days,
            "over_30_days": sum(1 for r in rows if r["sla_flag"] == "over_30"),
        }
    }


# ── Committed vs Buyout ────────────────────────────────────────────────────────

@router.get("/committed-vs-buyout")
def committed_vs_buyout(org_ctx=Depends(get_current_org), db: Session = Depends(get_db),
                        project_id: int = None):
    """Committed costs vs budget — shows procurement savings/overruns by category."""
    org = _get_org(org_ctx, db)
    projects = {p.id: p for p in db.query(Project).filter(Project.org_id == org.id).all()}
    if project_id:
        projects = {k: v for k, v in projects.items() if k == project_id}
    committed = db.query(CommittedCost).filter(CommittedCost.project_id.in_(projects.keys())).all()
    cats = db.query(CostCategory).filter(CostCategory.project_id.in_(projects.keys())).all()
    cat_map = {c.id: c for c in cats}

    # Group by category
    cat_data = defaultdict(lambda: {"budget": 0, "committed": 0, "invoiced": 0})
    for c in committed:
        if c.category_id and c.category_id in cat_map:
            name = cat_map[c.category_id].name
            budget = cat_map[c.category_id].budget or 0
        else:
            name = "Unallocated"
            budget = 0
        cat_data[name]["budget"] += budget
        cat_data[name]["committed"] += c.contract_amount
        cat_data[name]["invoiced"] += c.invoiced_to_date or 0

    rows = []
    for name, d in cat_data.items():
        buyout_savings = d["budget"] - d["committed"]
        rows.append({
            "category": name, "budget": round(d["budget"], 2),
            "committed": round(d["committed"], 2),
            "invoiced_to_date": round(d["invoiced"], 2),
            "uncommitted": round(max(0, d["committed"] - d["invoiced"]), 2),
            "buyout_savings": round(buyout_savings, 2),
            "over_budget": buyout_savings < 0,
        })
    rows.sort(key=lambda x: x["buyout_savings"])
    return {
        "rows": rows,
        "summary": {
            "total_budget": round(sum(r["budget"] for r in rows), 2),
            "total_committed": round(sum(r["committed"] for r in rows), 2),
            "total_invoiced": round(sum(r["invoiced_to_date"] for r in rows), 2),
            "total_savings": round(sum(r["buyout_savings"] for r in rows), 2),
            "over_budget_categories": sum(1 for r in rows if r["over_budget"]),
        }
    }


# ── Vendor Risk Dashboard ──────────────────────────────────────────────────────

@router.get("/vendor-risk")
def vendor_risk_dashboard(org_ctx=Depends(get_current_org), db: Session = Depends(get_db)):
    """Aggregated vendor risk: insurance, WSIB, bonds, payment status, lien exposure."""
    org = _get_org(org_ctx, db)
    today = date.today().isoformat()
    warn_date = (date.today() + timedelta(days=30)).isoformat()
    vendors = db.query(OrgVendor).filter(OrgVendor.org_id == org.id, OrgVendor.is_active == True).all()
    rows = []
    for v in vendors:
        flags = []
        risk_score = 0
        if v.insurance_expiry and v.insurance_expiry < today: flags.append("insurance_expired"); risk_score += 30
        elif v.insurance_expiry and v.insurance_expiry <= warn_date: flags.append("insurance_expiring"); risk_score += 10
        if v.wsib_expiry and v.wsib_expiry < today: flags.append("wsib_expired"); risk_score += 20
        elif v.wsib_expiry and v.wsib_expiry <= warn_date: flags.append("wsib_expiring"); risk_score += 5
        if not v.wsib_number and not v.wcb_number: flags.append("no_wsib_number"); risk_score += 10
        if not v.hst_number: flags.append("no_hst_number"); risk_score += 5
        if not v.cra_business_number: flags.append("no_cra_bn"); risk_score += 5
        rag = "red" if risk_score >= 30 else ("amber" if risk_score >= 10 else "green")
        rows.append({
            "vendor_id": v.id, "vendor_name": v.name, "trade": v.trade,
            "insurance_expiry": v.insurance_expiry, "wsib_expiry": v.wsib_expiry,
            "liability_limit": v.liability_limit, "risk_score": risk_score,
            "flags": flags, "rag": rag,
        })
    rows.sort(key=lambda x: -x["risk_score"])
    return {
        "vendors": rows,
        "summary": {
            "total": len(rows),
            "red": sum(1 for r in rows if r["rag"] == "red"),
            "amber": sum(1 for r in rows if r["rag"] == "amber"),
            "green": sum(1 for r in rows if r["rag"] == "green"),
        }
    }


# ── AI Lender Memo Generator ───────────────────────────────────────────────────

@router.post("/ai-lender-memo/{project_id}")
async def ai_lender_memo(project_id: int, body: dict = None,
                         org_ctx=Depends(get_current_org), db: Session = Depends(get_db),
                         user=Depends(get_current_user)):
    """Generate a professional lender draw recommendation memo using AI."""
    org = _get_org(org_ctx, db)
    proj = db.query(Project).filter(Project.id == project_id, Project.org_id == org.id).first()
    if not proj: raise HTTPException(404)

    # Gather project data
    invoices = db.query(Invoice).filter(Invoice.project_id == project_id, Invoice.status == "processed").all()
    draws = db.query(Draw).filter(Draw.project_id == project_id).order_by(Draw.draw_number.desc()).all()
    latest_draw = draws[0] if draws else None
    cos = db.query(ChangeOrder).filter(ChangeOrder.project_id == project_id).all()
    approved_cos = [c for c in cos if c.status == "approved"]
    covenants = db.query(LenderCovenant).filter(LenderCovenant.project_id == project_id).all()
    budget = proj.total_budget or 0
    revised = budget + sum(c.amount for c in approved_cos)
    total_invoiced = sum(i.lender_submitted_amt or i.total_due or 0 for i in invoices)
    total_approved = sum(i.lender_approved_amt or 0 for i in invoices)
    pct_complete = round(total_approved / revised * 100, 1) if revised > 0 else 0
    holdback = sum((i.lender_approved_amt or 0) * (i.holdback_pct or 10) / 100 for i in invoices)
    pending_cos_amt = sum(c.amount for c in cos if c.status == "pending")
    breached = [c for c in covenants if c.status == "breach"]

    context = f"""Project: {proj.name}
Address: {proj.address or 'N/A'}
Province: {proj.province or 'ON'}
Original Contract: ${budget:,.0f}
Approved Change Orders: ${sum(c.amount for c in approved_cos):,.0f} ({len(approved_cos)} COs)
Revised Contract: ${revised:,.0f}
Total Invoiced: ${total_invoiced:,.0f}
Lender Approved to Date: ${total_approved:,.0f} ({pct_complete}% of revised contract)
Holdback Held: ${holdback:,.0f}
Pending Change Orders: ${pending_cos_amt:,.0f}
Total Draws: {len(draws)}
Latest Draw: {f'Draw #{latest_draw.draw_number} — {latest_draw.status}' if latest_draw else 'None'}
Covenant Breaches: {len(breached)} — {', '.join(c.name for c in breached) if breached else 'None'}
Project End Date: {proj.end_date or 'TBD'}
"""
    draw_amount = body.get("draw_amount") if body else None
    draw_number = body.get("draw_number", len(draws) + 1) if body else len(draws) + 1
    extra_context = body.get("notes", "") if body else ""

    prompt = f"""You are a senior construction lending analyst at a Canadian bank. Write a concise, professional draw recommendation memo for the credit committee.

Project Data:
{context}
{f"Draw Amount Requested: ${draw_amount:,.0f}" if draw_amount else ""}
Additional Notes from Analyst: {extra_context}

Write a memo with these sections (use clear headers):
1. DRAW RECOMMENDATION (Approve/Approve with conditions/Decline + recommended advance amount)
2. PROJECT OVERVIEW (2-3 sentences: project status, % complete, key facts)
3. BUDGET ANALYSIS (budget position, COs, variance narrative, concerns if any)
4. COVENANT COMPLIANCE (covenant status, any exceptions)
5. RISK FACTORS (top 2-3 risks — specific and factual based on data)
6. CONDITIONS OF ADVANCE (any conditions before funds release)
7. ANALYST SIGN-OFF LINE

Be professional, direct, and use exact dollar figures. Flag any concerns clearly. Maximum 400 words. Canadian dollar amounts."""

    try:
        result = await call_gemini_api(
            {
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.3, "maxOutputTokens": 1024},
            }
        )
        memo_text = result["candidates"][0]["content"]["parts"][0]["text"].strip()
        return {
            "memo": memo_text,
            "project_name": proj.name,
            "draw_number": draw_number,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(500, f"Memo generation failed: {str(e)}")
