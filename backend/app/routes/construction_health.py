"""
AI Construction Accountant + Draw Package Generator
New routes appended to the project router.
"""
from collections import defaultdict
from datetime import datetime as dt
from typing import Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import (
    User, Project, Invoice, Draw, Claim, CommittedCost,
    CostCategory, InvoiceAllocation, LienWaiver, Organization,
    Payment,
)
from ..dependencies import get_current_user, get_current_org

router = APIRouter(prefix="/api/project", tags=["construction-health"])


# ── Shared project resolver ───────────────────────────────────────────────────

def _get_proj_by_id(project_id: int, user_id: int, db: Session) -> Project:
    p = db.query(Project).filter(Project.id == project_id, Project.user_id == user_id).first()
    if not p:
        raise HTTPException(404, "Project not found")
    return p


# ═══════════════════════════════════════════════════════════════════════════════
#  AI CONSTRUCTION ACCOUNTANT
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/ai/construction-health")
def construction_health(
    project_id: Optional[int] = None,
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Comprehensive project health check:
    overbilling, budget overruns, duplicate invoices,
    stale draws, missing lien waivers, cost trending, approval rates.
    Returns severity-coded alerts with recommended actions.
    """
    org, _ = org_ctx

    # Resolve project
    if project_id:
        proj = db.query(Project).filter(
            Project.id == project_id,
            Project.org_id == org.id,
        ).first()
    else:
        proj = db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.id.desc()).first()

    if not proj:
        return {"alerts": [], "score": 100, "summary": "No project selected."}

    alerts = []
    today = dt.utcnow().strftime("%Y-%m-%d")
    today_dt = dt.utcnow()

    # ── All processed invoices for this project ────────────────────────────────
    invs = db.query(Invoice).filter(
        Invoice.project_id == proj.id,
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
    ).all()

    draws = db.query(Draw).filter(Draw.project_id == proj.id).all()
    committed_costs = db.query(CommittedCost).filter(
        CommittedCost.project_id == proj.id,
        CommittedCost.status == "active",
    ).all()
    categories = db.query(CostCategory).filter(CostCategory.project_id == proj.id).all()
    waivers = db.query(LienWaiver).filter(LienWaiver.project_id == proj.id).all()

    # ── 1. OVERBILLING ────────────────────────────────────────────────────────
    vendor_invoiced: dict = defaultdict(float)
    for inv in invs:
        if inv.vendor_name:
            vendor_invoiced[inv.vendor_name.strip().lower()] += (inv.total_due or 0)

    for cc in committed_costs:
        if not cc.vendor:
            continue
        vk = cc.vendor.strip().lower()
        invoiced = vendor_invoiced.get(vk, 0)
        if invoiced > cc.contract_amount * 1.05:
            overage = invoiced - cc.contract_amount
            pct = round((invoiced / cc.contract_amount - 1) * 100, 1) if cc.contract_amount > 0 else 0
            alerts.append({
                "id": f"overbill_{cc.id}",
                "severity": "critical" if pct > 15 else "warning",
                "category": "overbilling",
                "icon": "fa-triangle-exclamation",
                "title": f"Overbilling — {cc.vendor}",
                "detail": (
                    f"Invoiced ${invoiced:,.0f} against contract ${cc.contract_amount:,.0f} "
                    f"({pct}% over budget)."
                ),
                "action": "Review vendor invoices and verify contract amendments exist.",
                "amount": round(overage, 2),
            })

    # ── 2. CATEGORY BUDGET OVERRUNS ───────────────────────────────────────────
    for cat in categories:
        if not cat.budget or cat.budget <= 0:
            continue
        cat_total = (
            db.query(func.coalesce(func.sum(InvoiceAllocation.amount), 0.0))
            .filter(InvoiceAllocation.category_id == cat.id)
            .scalar() or 0
        )
        if cat_total > cat.budget:
            overage = cat_total - cat.budget
            pct = round((cat_total / cat.budget - 1) * 100, 1)
            alerts.append({
                "id": f"budget_{cat.id}",
                "severity": "critical" if pct > 20 else "warning",
                "category": "budget_overrun",
                "icon": "fa-circle-dollar-to-slot",
                "title": f"Budget overrun — {cat.name}",
                "detail": f"Spent ${cat_total:,.0f} vs budget ${cat.budget:,.0f} ({pct}% over).",
                "action": "Review allocations or submit a change order to increase the budget.",
                "amount": round(overage, 2),
            })

    # ── 3. UNSUBMITTED INVOICES ───────────────────────────────────────────────
    unsubmitted = [i for i in invs if not i.draw_id]
    if unsubmitted:
        total_unsub = sum(i.total_due or 0 for i in unsubmitted)
        dates = [
            i.invoice_date or (str(i.processed_at)[:10] if i.processed_at else None)
            for i in unsubmitted
            if i.invoice_date or i.processed_at
        ]
        oldest = min(dates) if dates else None
        alerts.append({
            "id": "unsubmitted",
            "severity": "warning" if total_unsub > 10000 else "info",
            "category": "unsubmitted",
            "icon": "fa-file-invoice",
            "title": f"{len(unsubmitted)} invoices not assigned to a draw",
            "detail": (
                f"${total_unsub:,.0f} in processed invoices have not been submitted to a lender draw."
                + (f" Oldest: {oldest}." if oldest else "")
            ),
            "action": "Assign these invoices to a draw for your next lender submission.",
            "amount": round(total_unsub, 2),
        })

    # ── 4. DUPLICATE INVOICES ─────────────────────────────────────────────────
    seen: dict = {}
    for inv in invs:
        if not inv.invoice_number:
            continue
        key = (
            (inv.vendor_name or "").strip().lower(),
            round(inv.total_due or 0, 2),
            inv.invoice_number.strip(),
        )
        if key in seen:
            alerts.append({
                "id": f"dup_{inv.id}",
                "severity": "critical",
                "category": "duplicate",
                "icon": "fa-copy",
                "title": f"Possible duplicate — {inv.vendor_name or 'Unknown vendor'}",
                "detail": (
                    f"Invoice #{inv.invoice_number} for ${inv.total_due or 0:,.2f} "
                    f"appears more than once."
                ),
                "action": "Review and delete the duplicate before your next draw submission.",
                "amount": round(inv.total_due or 0, 2),
            })
        else:
            seen[key] = inv.id

    # ── 5. STALE DRAWS ────────────────────────────────────────────────────────
    for draw in draws:
        if draw.submission_date and draw.status not in ("approved", "partial"):
            try:
                sub_dt = dt.strptime(draw.submission_date, "%Y-%m-%d")
                days = (today_dt - sub_dt).days
                if days > 30:
                    alerts.append({
                        "id": f"stale_draw_{draw.id}",
                        "severity": "warning",
                        "category": "stale_draw",
                        "icon": "fa-hourglass-half",
                        "title": f"Draw #{draw.draw_number} awaiting approval for {days} days",
                        "detail": f"Submitted {draw.submission_date}. No lender approval after {days} days.",
                        "action": "Follow up with your lender. Cash flow may be impacted.",
                        "amount": None,
                    })
            except (ValueError, TypeError):
                pass

    # ── 6. MISSING LIEN WAIVERS ───────────────────────────────────────────────
    waiver_vendors = {(w.vendor_name or "").strip().lower() for w in waivers}
    threshold = max((proj.total_budget or 0) * 0.02, 5000)
    large_vendor: dict = defaultdict(float)
    for inv in invs:
        large_vendor[(inv.vendor_name or "").strip().lower()] += (inv.total_due or 0)

    for vk, total in large_vendor.items():
        if total > threshold and vk not in waiver_vendors and vk:
            alerts.append({
                "id": f"waiver_{vk[:20]}",
                "severity": "warning",
                "category": "lien_waiver",
                "icon": "fa-file-signature",
                "title": f"No lien waiver — {vk.title()}",
                "detail": f"${total:,.0f} invoiced but no lien waiver on file.",
                "action": "Request a lien waiver before releasing final payment.",
                "amount": None,
            })

    # ── 7. PROJECTED BUDGET OVERRUN ───────────────────────────────────────────
    total_invoiced = sum(i.total_due or 0 for i in invs)
    budget = proj.total_budget or 0
    if budget > 0 and total_invoiced > 0 and total_invoiced / budget > 0.85:
        remaining = budget - total_invoiced
        uncommitted = sum(
            cc.contract_amount - (cc.invoiced_to_date or 0)
            for cc in committed_costs
            if cc.contract_amount > (cc.invoiced_to_date or 0)
        )
        if uncommitted > remaining * 1.1:
            shortage = uncommitted - remaining
            alerts.append({
                "id": "cost_trend",
                "severity": "critical",
                "category": "cost_trend",
                "icon": "fa-chart-line",
                "title": "Projected budget overrun",
                "detail": (
                    f"Spent {round(total_invoiced/budget*100, 1)}% of budget. "
                    f"Outstanding commitments (${uncommitted:,.0f}) exceed remaining budget "
                    f"(${remaining:,.0f}) by ${shortage:,.0f}."
                ),
                "action": "Raise change orders with owner or seek additional funding.",
                "amount": round(shortage, 2),
            })

    # ── 8. LENDER APPROVAL RATE ───────────────────────────────────────────────
    if draws:
        total_submitted_amt = sum(
            db.query(func.coalesce(func.sum(Invoice.lender_submitted_amt), 0.0))
            .filter(Invoice.draw_id == d.id, Invoice.user_id == current_user.id)
            .scalar() or 0
            for d in draws
        )
        total_approved_amt = sum(
            db.query(func.coalesce(func.sum(Invoice.lender_approved_amt), 0.0))
            .filter(Invoice.draw_id == d.id, Invoice.user_id == current_user.id)
            .scalar() or 0
            for d in draws
        )
        if total_submitted_amt > 0 and total_approved_amt > 0:
            rate = total_approved_amt / total_submitted_amt
            if rate < 0.90:
                reduction_pct = round((1 - rate) * 100, 1)
                alerts.append({
                    "id": "approval_rate",
                    "severity": "info",
                    "category": "approval_rate",
                    "icon": "fa-percent",
                    "title": f"Lender approval rate {round(rate*100, 0):.0f}%",
                    "detail": (
                        f"Lender has reduced ${total_submitted_amt - total_approved_amt:,.0f} "
                        f"({reduction_pct}%) across all draws."
                    ),
                    "action": "Review consistently reduced line items and adjust future draw submissions.",
                    "amount": round(total_submitted_amt - total_approved_amt, 2),
                })

    # ── Score ─────────────────────────────────────────────────────────────────
    crit = sum(1 for a in alerts if a["severity"] == "critical")
    warn = sum(1 for a in alerts if a["severity"] == "warning")
    score = max(0, 100 - crit * 20 - warn * 8)
    label = (
        "Excellent" if score >= 90
        else "Good" if score >= 75
        else "Needs Attention" if score >= 55
        else "At Risk"
    )

    return {
        "project_name": proj.name,
        "score": score,
        "severity_label": label,
        "alert_count": len(alerts),
        "critical_count": crit,
        "warning_count": warn,
        "alerts": sorted(alerts, key=lambda a: {"critical": 0, "warning": 1, "info": 2}[a["severity"]]),
        "totals": {
            "invoiced": round(total_invoiced, 2),
            "budget": round(budget, 2),
            "spend_pct": round(total_invoiced / budget * 100, 1) if budget > 0 else 0,
        },
    }


# ═══════════════════════════════════════════════════════════════════════════════
#  DRAW PACKAGE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

@router.get("/draws/{draw_id}/package")
def generate_draw_package(
    draw_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Return a print-ready HTML draw package for lender submission.
    Open in a new browser tab and use Ctrl+P / Cmd+P to save as PDF.
    """
    draw = (
        db.query(Draw)
        .join(Project, Project.id == Draw.project_id)
        .filter(Draw.id == draw_id, Project.user_id == current_user.id)
        .first()
    )
    if not draw:
        raise HTTPException(404, "Draw not found")

    proj = db.query(Project).filter(Project.id == draw.project_id).first()
    org = (
        db.query(Organization).filter(Organization.id == proj.org_id).first()
        if proj and proj.org_id else None
    )

    invs = (
        db.query(Invoice)
        .filter(
            Invoice.draw_id == draw_id,
            Invoice.user_id == current_user.id,
            Invoice.status == "processed",
        )
        .order_by(Invoice.vendor_name, Invoice.invoice_date)
        .all()
    )

    total_inv   = sum(i.total_due or 0 for i in invs)
    total_sub   = sum(i.lender_submitted_amt or 0 for i in invs)
    total_hold  = sum((i.lender_submitted_amt or 0) * (i.holdback_pct or 0) / 100 for i in invs)
    total_net   = total_sub - total_hold
    total_appro = sum(i.lender_approved_amt or 0 for i in invs)

    gen_date = dt.utcnow().strftime("%B %d, %Y")
    org_name = org.name if org else (proj.client or "")
    proj_name = proj.name if proj else "Project"
    proj_code = proj.code or ""
    proj_addr = proj.address or ""
    lender_budget = f"${proj.lender_budget:,.2f}" if proj and proj.lender_budget else "—"
    total_budget  = f"${proj.total_budget:,.2f}" if proj and proj.total_budget else "—"

    # Invoice rows
    rows = ""
    for idx, inv in enumerate(invs, 1):
        submitted = inv.lender_submitted_amt or 0
        holdback  = submitted * (inv.holdback_pct or 0) / 100
        net       = submitted - holdback
        sc = {"approved": "#16a34a", "rejected": "#dc2626", "partial": "#d97706"}.get(
            inv.lender_status or "", "#6b7280"
        )
        rows += (
            f'<tr>'
            f'<td class="tc gray sm">{idx}</td>'
            f'<td class="sm">{inv.vendor_name or "—"}</td>'
            f'<td class="sm mono">{inv.invoice_number or "—"}</td>'
            f'<td class="sm">{inv.invoice_date or "—"}</td>'
            f'<td class="tr sm">${inv.total_due or 0:,.2f}</td>'
            f'<td class="tr sm">${submitted:,.2f}</td>'
            f'<td class="tr sm">{inv.holdback_pct or 0:.0f}%</td>'
            f'<td class="tr sm">${holdback:,.2f}</td>'
            f'<td class="tr sm bold">${net:,.2f}</td>'
            f'<td class="sm bold" style="color:{sc}">{(inv.lender_status or "pending").upper()}</td>'
            f'</tr>'
        )

    holdback_rate = round(total_hold / total_sub * 100, 1) if total_sub > 0 else 0
    budget_pct = round(total_sub / proj.total_budget * 100, 1) if proj and proj.total_budget else 0
    notes_html = (
        f'<div class="section"><h2>Notes</h2>'
        f'<div class="note-box">{draw.notes}</div></div>'
        if draw.notes else ""
    )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8"/>
<title>Draw #{draw.draw_number} Package — {proj_name}</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box;}}
body{{font-family:Arial,Helvetica,sans-serif;font-size:13px;color:#1e293b;background:#fff;}}
@media print{{
  body{{-webkit-print-color-adjust:exact;print-color-adjust:exact;}}
  .no-print{{display:none!important;}}
}}
.wrap{{max-width:1050px;margin:0 auto;padding:36px 32px;}}
.print-btn{{position:fixed;bottom:24px;right:24px;background:#00acff;color:#fff;border:none;
  padding:12px 24px;border-radius:10px;font-size:14px;font-weight:700;cursor:pointer;
  box-shadow:0 4px 16px rgba(0,172,255,.4);z-index:999;}}
.header{{background:linear-gradient(135deg,#005366 0%,#00acff 100%);color:#fff;
  padding:28px 32px;border-radius:12px;margin-bottom:24px;}}
.header h1{{font-size:22px;font-weight:700;margin-bottom:4px;}}
.header p{{font-size:12px;opacity:.85;}}
.section{{margin-bottom:22px;}}
h2{{font-size:12px;font-weight:700;color:#334155;text-transform:uppercase;
  letter-spacing:.06em;border-bottom:2px solid #00acff;padding-bottom:5px;margin-bottom:12px;}}
.grid-2{{display:grid;grid-template-columns:1fr 1fr;gap:12px;}}
.grid-4{{display:grid;grid-template-columns:repeat(4,1fr);gap:10px;margin-bottom:16px;}}
.info-box{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:7px;padding:12px;}}
.info-box .lbl{{font-size:9px;font-weight:700;text-transform:uppercase;color:#94a3b8;letter-spacing:.06em;margin-bottom:2px;}}
.info-box .val{{font-size:13px;font-weight:700;color:#1e293b;}}
.card{{border:1px solid #e2e8f0;border-radius:8px;padding:12px;text-align:center;}}
.card .lbl{{font-size:9px;color:#94a3b8;text-transform:uppercase;font-weight:700;margin-bottom:3px;}}
.card .val{{font-size:17px;font-weight:700;color:#1e293b;}}
.card.green .val{{color:#16a34a;}}.card.blue .val{{color:#0284c7;}}.card.red .val{{color:#dc2626;}}
table{{width:100%;border-collapse:collapse;}}
thead tr{{background:#1e293b;color:#fff;}}
thead th{{padding:8px 9px;font-size:10px;font-weight:700;text-transform:uppercase;letter-spacing:.04em;text-align:left;}}
.tr{{text-align:right;}}.tc{{text-align:center;}}.bold{{font-weight:700;}}
.sm{{font-size:11px;padding:6px 9px;border-bottom:1px solid #f0f0f0;}}
.gray{{color:#6b7280;}}.mono{{font-family:monospace;}}
.totals-row td{{background:#f1f5f9;font-weight:700;font-size:12px;padding:9px;border-top:2px solid #334155;}}
.net-box{{background:#f0fdf4;border:2px solid #16a34a;border-radius:10px;padding:20px;
  display:flex;justify-content:space-between;align-items:center;}}
.net-amount{{font-size:26px;font-weight:700;color:#15803d;}}
.sig-grid{{display:grid;grid-template-columns:1fr 1fr;gap:40px;margin-top:44px;}}
.sig{{border-top:2px solid #334155;padding-top:8px;font-size:11px;color:#64748b;}}
.sig strong{{display:block;margin-bottom:22px;font-size:12px;color:#1e293b;}}
.note-box{{background:#f8fafc;border:1px solid #e2e8f0;border-radius:8px;padding:14px;font-size:12px;line-height:1.6;}}
.badge{{display:inline-block;padding:2px 8px;border-radius:10px;font-size:10px;font-weight:700;}}
.badge-submitted{{background:#fef3c7;color:#d97706;}}
.badge-approved{{background:#dcfce7;color:#16a34a;}}
.badge-draft{{background:#f1f5f9;color:#64748b;}}
.footer{{margin-top:36px;text-align:center;font-size:10px;color:#94a3b8;border-top:1px solid #f0f0f0;padding-top:14px;}}
</style>
</head>
<body>

<button class="print-btn no-print" onclick="window.print()">🖨&nbsp; Print / Save PDF</button>

<div class="wrap">

  <div class="header">
    <h1>Draw #{draw.draw_number} &mdash; Progress Draw Submission</h1>
    <p>{proj_name} &nbsp;&bull;&nbsp; {org_name} &nbsp;&bull;&nbsp; Generated {gen_date}</p>
  </div>

  <div class="section">
    <h2>Project Information</h2>
    <div class="grid-2">
      <div class="info-box"><div class="lbl">Project</div><div class="val">{proj_name}</div></div>
      <div class="info-box"><div class="lbl">Code</div><div class="val">{proj_code or "—"}</div></div>
      <div class="info-box"><div class="lbl">Address</div><div class="val">{proj_addr or "—"}</div></div>
      <div class="info-box"><div class="lbl">Organization</div><div class="val">{org_name or "—"}</div></div>
      <div class="info-box"><div class="lbl">Total Budget</div><div class="val">{total_budget}</div></div>
      <div class="info-box"><div class="lbl">Lender Budget</div><div class="val">{lender_budget}</div></div>
    </div>
  </div>

  <div class="section">
    <h2>Draw Information</h2>
    <div class="grid-2">
      <div class="info-box"><div class="lbl">Draw Number</div><div class="val">#{draw.draw_number}</div></div>
      <div class="info-box"><div class="lbl">Status</div><div class="val">
        <span class="badge badge-{draw.status or 'draft'}">{(draw.status or 'draft').upper()}</span>
      </div></div>
      <div class="info-box"><div class="lbl">Submission Date</div><div class="val">{draw.submission_date or "—"}</div></div>
      <div class="info-box"><div class="lbl">FX Rate</div><div class="val">{draw.fx_rate or 1.0}</div></div>
    </div>
  </div>

  <div class="grid-4">
    <div class="card"><div class="lbl">Invoices</div><div class="val">{len(invs)}</div></div>
    <div class="card blue"><div class="lbl">Total Invoiced</div><div class="val">${total_inv:,.0f}</div></div>
    <div class="card"><div class="lbl">Submitted</div><div class="val">${total_sub:,.0f}</div></div>
    <div class="card red"><div class="lbl">Holdback</div><div class="val">${total_hold:,.0f}</div></div>
  </div>

  <div class="section">
    <h2>Invoice Schedule</h2>
    <table>
      <thead>
        <tr>
          <th class="tc">#</th><th>Vendor</th><th>Invoice #</th><th>Date</th>
          <th class="tr">Invoiced</th><th class="tr">Submitted</th>
          <th class="tr">HB%</th><th class="tr">HB $</th>
          <th class="tr">Net Claim</th><th>Status</th>
        </tr>
      </thead>
      <tbody>
        {rows}
        <tr class="totals-row">
          <td colspan="4" style="padding:9px;font-weight:700;">TOTALS</td>
          <td class="tr">${total_inv:,.2f}</td>
          <td class="tr">${total_sub:,.2f}</td>
          <td class="tr">—</td>
          <td class="tr">${total_hold:,.2f}</td>
          <td class="tr" style="color:#16a34a;">${total_net:,.2f}</td>
          <td></td>
        </tr>
      </tbody>
    </table>
  </div>

  <div class="section">
    <h2>Net Claim Summary</h2>
    <div class="net-box">
      <div>
        <div style="font-size:11px;color:#16a34a;font-weight:700;margin-bottom:3px;">AMOUNT REQUESTED FROM LENDER</div>
        <div class="net-amount">${total_net:,.2f} CAD</div>
        <div style="font-size:11px;color:#6b7280;margin-top:4px;">
          Submitted ${total_sub:,.2f} &nbsp;less holdback ${total_hold:,.2f}
          {f" &nbsp;&bull;&nbsp; Approved ${total_appro:,.2f}" if total_appro else ""}
        </div>
      </div>
      <div style="text-align:right;font-size:11px;color:#6b7280;">
        <div>Holdback rate: {holdback_rate}%</div>
        <div style="margin-top:4px;">Draw as % of lender budget:</div>
        <div style="font-size:18px;font-weight:700;color:#1e293b;">{budget_pct}%</div>
      </div>
    </div>
  </div>

  {notes_html}

  <div class="sig-grid">
    <div class="sig">
      <strong>Submitted by (General Contractor)</strong>
      Name: ________________________________<br/><br/>
      Signature: ________________________________<br/><br/>
      Date: ________________________________<br/>
      <div style="margin-top:8px;font-size:10px;">I certify the amounts claimed are accurate and all work has been performed in accordance with the contract.</div>
    </div>
    <div class="sig">
      <strong>Reviewed by (Lender / Consultant)</strong>
      Name: ________________________________<br/><br/>
      Signature: ________________________________<br/><br/>
      Date: ________________________________<br/>
      <div style="margin-top:8px;font-size:10px;">
        Authorized: $____________________ &nbsp; Holdback: $____________________
      </div>
    </div>
  </div>

  <div class="footer">
    Generated by Finel AI Projects &nbsp;&bull;&nbsp; projects.finel.ai &nbsp;&bull;&nbsp; {gen_date}
  </div>
</div>
</body>
</html>"""

    return HTMLResponse(content=html, media_type="text/html")
