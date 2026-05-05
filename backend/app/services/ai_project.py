"""AI-powered project finance intelligence.

Feature 1:  Invoice → Cost Code Mapper (Gemini)
Feature 2:  Lien & Holdback Compliance Brain (Canada rule engine)
Feature 3:  Cost Overrun Early Warning (spending velocity)
Feature 4:  Draw Intelligence Engine (draw readiness checklist)
Feature 5:  Cash Flow Reality Simulator (scenario modeling)
Feature 6:  Subcontractor Risk Score (rule-based scoring)
Feature 7:  Lender Behavior Model (rejection pattern detection)
Feature 8:  Draw Approval Probability Score (pre-submission risk per invoice)
Feature 9:  Closeout Readiness Agent (real-time closeout checklist)
Feature 10: Government Claim Optimizer (lender vs provincial vs federal cost split)
Feature 11: Cost Consultant in a Box (Gemini monthly commentary)
Feature 12: Change Order Early Warning Radar (detect COs before formal issue)
Feature 13: Vendor Risk Memory (cross-project vendor risk profiles)
"""
from __future__ import annotations
import json
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _today() -> str:
    return datetime.utcnow().strftime("%Y-%m-%d")

def _days_between(a: str, b: str) -> Optional[int]:
    try:
        return (datetime.strptime(b, "%Y-%m-%d") - datetime.strptime(a, "%Y-%m-%d")).days
    except Exception:
        return None


# ─── Feature 1: Invoice → Cost Code AI Mapper ────────────────────────────────

def suggest_allocation(invoice: Any, categories: List[Any], db: Any) -> dict:
    """Use Gemini to suggest the best cost category + sub-category for an invoice.
    Falls back gracefully if no API key is available."""
    from .gemini import _env_keys
    from ..models import GeminiApiKey

    # Build category list for the prompt
    cat_list = []
    for cat in categories:
        entry = {"id": cat.id, "name": cat.name, "subcategories": []}
        for sc in getattr(cat, "sub_categories", []):
            entry["subcategories"].append({"id": sc.id, "name": sc.name})
        cat_list.append(entry)

    if not cat_list:
        return {"error": "No cost categories defined for this project"}

    # Gather available keys (env first, then DB pool)
    api_keys = _env_keys()
    if not api_keys:
        db_keys = db.query(GeminiApiKey).filter(GeminiApiKey.is_active == True).order_by(GeminiApiKey.priority).all()
        api_keys = [k.key_value for k in db_keys]
    if not api_keys:
        return {"error": "No Gemini API key available"}

    # Build invoice context
    inv_context = {
        "vendor": invoice.vendor_name or "Unknown",
        "total": invoice.total_due or 0,
        "description": None,
        "line_items": [],
    }
    if invoice.extracted_data:
        data = invoice.extracted_data if isinstance(invoice.extracted_data, dict) else {}
        inv_context["description"] = data.get("description") or data.get("notes")
        items = data.get("line_items") or data.get("items") or []
        if isinstance(items, list):
            inv_context["line_items"] = [
                i.get("description") or i.get("name") or str(i)
                for i in items[:5] if isinstance(i, dict)
            ]

    prompt = f"""You are a construction project finance controller.
Given this invoice and the available cost categories, suggest the single best matching category and sub-category.

INVOICE:
- Vendor: {inv_context['vendor']}
- Amount: ${inv_context['total']:,.2f}
- Description: {inv_context['description'] or 'Not provided'}
- Line items: {', '.join(inv_context['line_items']) if inv_context['line_items'] else 'Not provided'}

AVAILABLE CATEGORIES:
{json.dumps(cat_list, indent=2)}

Respond with ONLY valid JSON in this exact format:
{{
  "category_id": <integer id>,
  "category_name": "<name>",
  "sub_category_id": <integer id or null>,
  "sub_category_name": "<name or null>",
  "confidence": <float 0.0-1.0>,
  "reasoning": "<one sentence>"
}}"""

    import google.generativeai as genai
    last_err = None
    for key in api_keys:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-1.5-flash")
            resp = model.generate_content(prompt)
            text = resp.text.strip()
            # Strip markdown code fences if present
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            result = json.loads(text.strip())
            # Validate category_id belongs to this project
            valid_cat_ids = {c.id for c in categories}
            if result.get("category_id") not in valid_cat_ids:
                result["category_id"] = None
                result["confidence"] = 0.1
                result["reasoning"] = "AI suggestion not valid for this project — please assign manually."
            return result
        except Exception as e:
            last_err = str(e)
            logger.warning("Gemini key failed for suggest_allocation: %s", e)
            continue

    return {"error": f"AI suggestion failed: {last_err}"}


# ─── Feature 2: Lien & Holdback Compliance Brain ─────────────────────────────

# Canadian holdback rules by province (Construction Acts)
_PROVINCE_RULES = {
    "ON": {
        "name": "Ontario",
        "act": "Construction Act (Ontario)",
        "holdback_pct": 10,
        "release_days_after_substantial": 45,
        "lien_period_days": 60,         # from publication of Certificate of Substantial Performance
        "preservation_days": 90,        # to preserve lien by action
        "notes": "10% holdback mandatory. Lien period 60 days from last supply date or publication of CSP.",
    },
    "BC": {
        "name": "British Columbia",
        "act": "Builders Lien Act (BC)",
        "holdback_pct": 10,
        "release_days_after_substantial": 55,
        "lien_period_days": 45,
        "preservation_days": None,
        "notes": "10% holdback. Head contractor has 55 days after completion to release; 45-day lien filing period.",
    },
    "AB": {
        "name": "Alberta",
        "act": "Builders' Lien Act (Alberta)",
        "holdback_pct": 10,
        "release_days_after_substantial": 45,
        "lien_period_days": 45,
        "preservation_days": 180,
        "notes": "10% holdback. 45-day lien period from last supply. Preserve lien by action within 180 days.",
    },
    "QC": {
        "name": "Quebec",
        "act": "Civil Code of Quebec (Legal Hypothec)",
        "holdback_pct": 0,             # No statutory holdback — contractual only
        "release_days_after_substantial": 30,
        "lien_period_days": 30,        # 30 days from end of work to publish legal hypothec
        "preservation_days": 180,
        "notes": "No statutory holdback. Legal hypothec must be published within 30 days of end of work.",
    },
    "MB": {
        "name": "Manitoba",
        "act": "Builders' Liens Act (Manitoba)",
        "holdback_pct": 7.5,
        "release_days_after_substantial": 40,
        "lien_period_days": 40,
        "preservation_days": None,
        "notes": "7.5% holdback. 40-day lien filing period from last supply date.",
    },
    "SK": {
        "name": "Saskatchewan",
        "act": "Builders' Lien Act (Saskatchewan)",
        "holdback_pct": 10,
        "release_days_after_substantial": 40,
        "lien_period_days": 40,
        "preservation_days": None,
        "notes": "10% holdback. 40-day lien period from last supply.",
    },
    "NS": {
        "name": "Nova Scotia",
        "act": "Builders' Lien Act (NS)",
        "holdback_pct": 10,
        "release_days_after_substantial": 45,
        "lien_period_days": 45,
        "preservation_days": None,
        "notes": "10% holdback. 45-day lien period.",
    },
    "NB": {
        "name": "New Brunswick",
        "act": "Mechanics' Lien Act (NB)",
        "holdback_pct": 10,
        "release_days_after_substantial": 45,
        "lien_period_days": 60,
        "preservation_days": None,
        "notes": "10% holdback. 60-day lien filing period.",
    },
}


def compliance_alerts(project: Any, invoices: List[Any], draws: List[Any], lien_waivers: List[Any]) -> dict:
    """Generate Canadian construction compliance alerts for holdback and lien timelines."""
    today = _today()
    province = "ON"  # default to Ontario; could be derived from project.address in future
    if project.address:
        addr = project.address.upper()
        for code in _PROVINCE_RULES:
            if code in addr or _PROVINCE_RULES[code]["name"].upper() in addr:
                province = code
                break

    rules = _PROVINCE_RULES.get(province, _PROVINCE_RULES["ON"])
    alerts = []
    info = []

    # --- Holdback alerts ---
    unreleased = [i for i in invoices if not getattr(i, "holdback_released", False)
                  and (getattr(i, "holdback_pct", 0) or 0) > 0]

    holdback_eligible = []
    for inv in unreleased:
        inv_date = inv.invoice_date or (str(inv.processed_at)[:10] if inv.processed_at else None)
        if not inv_date:
            continue
        days_old = _days_between(inv_date, today)
        if days_old is None:
            continue
        # Check if enough time has passed to potentially release holdback
        threshold = rules["release_days_after_substantial"]
        if days_old >= threshold:
            holdback_eligible.append({
                "invoice_id": inv.id,
                "vendor": inv.vendor_name or "Unknown",
                "date": inv_date,
                "days_old": days_old,
                "holdback_amt": round((inv.subtotal or inv.total_due or 0) * (inv.holdback_pct or 0) / 100, 2),
            })

    if holdback_eligible:
        total_eligible = sum(e["holdback_amt"] for e in holdback_eligible)
        alerts.append({
            "severity": "warning",
            "type": "holdback_release_eligible",
            "title": f"Holdback Release Eligible — ${total_eligible:,.2f}",
            "message": f"{len(holdback_eligible)} invoice(s) are past the {threshold}-day holdback period under the {rules['act']}. Total holdback eligible for release: ${total_eligible:,.2f}.",
            "items": holdback_eligible[:5],
            "action": "Review and release holdback for eligible invoices",
            "province": province,
            "rule": rules["act"],
        })

    # Holdback approaching eligibility (within 14 days)
    approaching = []
    for inv in unreleased:
        inv_date = inv.invoice_date or (str(inv.processed_at)[:10] if inv.processed_at else None)
        if not inv_date:
            continue
        days_old = _days_between(inv_date, today)
        if days_old is None:
            continue
        threshold = rules["release_days_after_substantial"]
        days_remaining = threshold - days_old
        if 0 < days_remaining <= 14:
            approaching.append({
                "invoice_id": inv.id,
                "vendor": inv.vendor_name or "Unknown",
                "date": inv_date,
                "days_remaining": days_remaining,
                "holdback_amt": round((inv.subtotal or inv.total_due or 0) * (inv.holdback_pct or 0) / 100, 2),
            })
    if approaching:
        alerts.append({
            "severity": "info",
            "type": "holdback_approaching",
            "title": f"Holdback Eligibility Approaching — {len(approaching)} invoice(s)",
            "message": f"{len(approaching)} invoice(s) will be eligible for holdback release within 14 days.",
            "items": approaching[:5],
            "action": "Prepare holdback release documentation",
            "province": province,
            "rule": rules["act"],
        })

    # --- Lien period alerts (invoices with no lien waiver) ---
    waiver_invoice_ids = set()
    for w in lien_waivers:
        # If waiver has a draw_id, match invoices in that draw
        pass  # broad coverage — check vendor instead
    waiver_vendors = {(w.vendor_name or "").lower() for w in lien_waivers if w.vendor_name}

    lien_risk = []
    for inv in invoices:
        vendor = (inv.vendor_name or "").lower()
        if vendor in waiver_vendors:
            continue
        inv_date = inv.invoice_date or (str(inv.processed_at)[:10] if inv.processed_at else None)
        if not inv_date:
            continue
        days_old = _days_between(inv_date, today)
        if days_old is None:
            continue
        lien_window = rules["lien_period_days"]
        days_remaining = lien_window - days_old
        if 0 < days_remaining <= 21:  # warn 21 days before lien period closes
            lien_risk.append({
                "invoice_id": inv.id,
                "vendor": inv.vendor_name or "Unknown",
                "date": inv_date,
                "days_remaining": days_remaining,
                "amount": inv.total_due or 0,
            })

    if lien_risk:
        alerts.append({
            "severity": "high",
            "type": "lien_window_closing",
            "title": f"Lien Filing Window Closing — {len(lien_risk)} vendor(s)",
            "message": f"{len(lien_risk)} unpaid vendor(s) can file a lien within the next 21 days. Collect unconditional lien waivers or pay outstanding balances.",
            "items": lien_risk[:5],
            "action": "Collect lien waivers or issue payment",
            "province": province,
            "rule": rules["act"],
        })

    # --- Missing lien waivers on funded draws ---
    for draw in draws:
        if draw.status not in ("approved", "funded"):
            continue
        draw_invs = [i for i in invoices if i.draw_id == draw.id]
        draw_vendors = {(i.vendor_name or "").lower() for i in draw_invs if i.vendor_name}
        covered = {(w.vendor_name or "").lower() for w in lien_waivers
                   if w.draw_id == draw.id and w.vendor_name and w.waiver_type == "unconditional"}
        missing = draw_vendors - covered
        if missing:
            alerts.append({
                "severity": "warning",
                "type": "missing_lien_waiver",
                "title": f"Draw {draw.draw_number} — Missing Unconditional Lien Waivers",
                "message": f"{len(missing)} vendor(s) in funded Draw {draw.draw_number} have no unconditional lien waiver on file.",
                "items": [{"vendor": v} for v in list(missing)[:5]],
                "action": "Collect unconditional lien waivers before draw close-out",
                "province": province,
                "rule": rules["act"],
            })

    # Info block
    info.append({
        "province": province,
        "province_name": rules["name"],
        "act": rules["act"],
        "holdback_pct": rules["holdback_pct"],
        "release_days": rules["release_days_after_substantial"],
        "lien_period_days": rules["lien_period_days"],
        "notes": rules["notes"],
    })

    total_holdback_held = sum(
        round((i.subtotal or i.total_due or 0) * (getattr(i, "holdback_pct", 0) or 0) / 100, 2)
        for i in unreleased
    )

    return {
        "alerts": alerts,
        "alert_count": len(alerts),
        "province": province,
        "rules": info[0] if info else {},
        "holdback_summary": {
            "total_held": round(total_holdback_held, 2),
            "unreleased_count": len(unreleased),
            "eligible_count": len(holdback_eligible),
        },
    }


# ─── Feature 3: Cost Overrun Early Warning ───────────────────────────────────

def overrun_alerts(project: Any, categories: List[Any], allocations_by_cat: Dict[int, float],
                   change_orders_by_cat: Dict[int, float]) -> dict:
    """Detect categories trending toward budget overrun based on spend velocity."""
    today = _today()
    alerts = []

    start = project.start_date
    end = project.end_date

    # Project timeline progress
    timeline_pct = None
    if start and end:
        total_days = _days_between(start, end)
        elapsed = _days_between(start, today)
        if total_days and total_days > 0 and elapsed is not None:
            timeline_pct = max(0.0, min(100.0, round(elapsed / total_days * 100, 1)))

    category_alerts = []
    for cat in categories:
        co_adj = change_orders_by_cat.get(cat.id, 0.0)
        revised_budget = cat.budget + co_adj
        invoiced = allocations_by_cat.get(cat.id, 0.0)

        if revised_budget <= 0:
            continue

        pct_spent = invoiced / revised_budget * 100
        remaining = revised_budget - invoiced

        severity = None
        message = None

        # Velocity-based: if we've spent more than timeline % with timeline data
        if timeline_pct is not None and timeline_pct > 10:
            if pct_spent > (timeline_pct + 20):
                severity = "high"
                message = f"Spending is {pct_spent:.0f}% of budget but project is only {timeline_pct:.0f}% through its timeline."
            elif pct_spent > (timeline_pct + 10):
                severity = "warning"
                message = f"Spending is {pct_spent:.0f}% of budget vs {timeline_pct:.0f}% project completion — running ahead of schedule."

        # Hard threshold: >90% spent
        if pct_spent >= 95:
            severity = "high"
            message = f"Budget nearly exhausted — {pct_spent:.0f}% spent, only ${remaining:,.2f} remaining."
        elif pct_spent >= 80 and severity != "high":
            severity = "warning"
            message = f"{pct_spent:.0f}% of budget consumed. ${remaining:,.2f} remaining."

        # Over budget
        if invoiced > revised_budget:
            overrun = invoiced - revised_budget
            severity = "critical"
            message = f"OVER BUDGET by ${overrun:,.2f} ({pct_spent:.0f}% of budget spent)."

        if severity:
            projected_final = None
            if timeline_pct and timeline_pct > 5:
                # Linear projection: if we've spent X at Y% timeline, project final = X / (Y/100)
                projected_final = round(invoiced / (timeline_pct / 100), 2) if timeline_pct > 0 else None

            category_alerts.append({
                "category_id": cat.id,
                "category_name": cat.name,
                "severity": severity,
                "budget": round(revised_budget, 2),
                "invoiced": round(invoiced, 2),
                "remaining": round(remaining, 2),
                "pct_spent": round(pct_spent, 1),
                "projected_final": projected_final,
                "projected_overrun": round(projected_final - revised_budget, 2) if projected_final else None,
                "message": message,
            })

    # Sort by severity
    sev_order = {"critical": 0, "high": 1, "warning": 2}
    category_alerts.sort(key=lambda a: sev_order.get(a["severity"], 9))

    # Overall project burn rate
    total_budget = sum(c.budget + change_orders_by_cat.get(c.id, 0.0) for c in categories)
    total_invoiced = sum(allocations_by_cat.values())
    overall_pct = round(total_invoiced / total_budget * 100, 1) if total_budget else 0

    return {
        "alerts": category_alerts,
        "alert_count": len(category_alerts),
        "critical_count": sum(1 for a in category_alerts if a["severity"] == "critical"),
        "high_count": sum(1 for a in category_alerts if a["severity"] == "high"),
        "warning_count": sum(1 for a in category_alerts if a["severity"] == "warning"),
        "overall_pct_spent": overall_pct,
        "timeline_pct": timeline_pct,
        "total_budget": round(total_budget, 2),
        "total_invoiced": round(total_invoiced, 2),
    }


# ─── Feature 4: Draw Intelligence Engine ─────────────────────────────────────

def draw_readiness(draw: Any, invoices: List[Any], lien_waivers: List[Any],
                   subcontractors: List[Any], documents: List[Any]) -> dict:
    """Generate a draw submission readiness checklist — what's ready vs. what's blocking."""
    checklist = []
    blocking = []
    ready = []
    warnings = []

    # 1. Invoice approval status
    pending_approval = [i for i in invoices if i.approval_status == "pending"]
    if pending_approval:
        item = {
            "check": "invoice_approvals",
            "label": "Invoice Approvals",
            "status": "blocking",
            "detail": f"{len(pending_approval)} invoice(s) still pending internal approval.",
            "items": [{"id": i.id, "vendor": i.vendor_name, "amount": i.total_due} for i in pending_approval[:5]],
        }
        blocking.append(item)
    else:
        ready.append({"check": "invoice_approvals", "label": "Invoice Approvals", "status": "ready", "detail": "All invoices approved."})

    # 2. Lender submitted amounts set
    no_submitted = [i for i in invoices if i.lender_submitted_amt is None]
    if no_submitted:
        blocking.append({
            "check": "lender_amounts",
            "label": "Lender Submitted Amounts",
            "status": "blocking",
            "detail": f"{len(no_submitted)} invoice(s) have no lender submitted amount set.",
            "items": [{"id": i.id, "vendor": i.vendor_name, "amount": i.total_due} for i in no_submitted[:5]],
        })
    else:
        ready.append({"check": "lender_amounts", "label": "Lender Submitted Amounts", "status": "ready", "detail": "All submitted amounts set."})

    # 3. Conditional lien waivers
    vendor_names = {(i.vendor_name or "").lower() for i in invoices if i.vendor_name}
    conditional_vendors = {
        (w.vendor_name or "").lower()
        for w in lien_waivers
        if w.draw_id == draw.id and w.waiver_type == "conditional" and w.vendor_name
    }
    missing_conditional = vendor_names - conditional_vendors
    if missing_conditional:
        warnings.append({
            "check": "conditional_waivers",
            "label": "Conditional Lien Waivers",
            "status": "warning",
            "detail": f"{len(missing_conditional)} vendor(s) missing conditional lien waivers.",
            "items": [{"vendor": v} for v in list(missing_conditional)[:5]],
        })
    else:
        ready.append({"check": "conditional_waivers", "label": "Conditional Lien Waivers", "status": "ready", "detail": "Conditional waivers collected from all vendors."})

    # 4. Insurance & WSIB on subcontractors
    today = _today()
    expired_subs = []
    for s in subcontractors:
        issues = []
        if s.insurance_expiry and s.insurance_expiry < today:
            issues.append(f"insurance expired {s.insurance_expiry}")
        if s.wsib_expiry and s.wsib_expiry < today:
            issues.append(f"WSIB expired {s.wsib_expiry}")
        if issues:
            expired_subs.append({"name": s.name, "issues": issues})
    if expired_subs:
        warnings.append({
            "check": "sub_compliance",
            "label": "Subcontractor Compliance",
            "status": "warning",
            "detail": f"{len(expired_subs)} subcontractor(s) have expired insurance or WSIB.",
            "items": expired_subs[:5],
        })
    else:
        ready.append({"check": "sub_compliance", "label": "Subcontractor Compliance", "status": "ready", "detail": "All subcontractors have valid insurance and WSIB."})

    # 5. Supporting documents
    draw_docs = [d for d in documents if d.draw_id == draw.id]
    if not draw_docs:
        warnings.append({
            "check": "draw_documents",
            "label": "Supporting Documents",
            "status": "warning",
            "detail": "No documents attached to this draw. Lenders typically require cost schedules and progress reports.",
        })
    else:
        ready.append({"check": "draw_documents", "label": "Supporting Documents", "status": "ready",
                      "detail": f"{len(draw_docs)} document(s) attached to this draw."})

    # 6. Draw has a submission date
    if not draw.submission_date:
        warnings.append({
            "check": "submission_date",
            "label": "Submission Date",
            "status": "warning",
            "detail": "No submission date set on this draw.",
        })
    else:
        ready.append({"check": "submission_date", "label": "Submission Date", "status": "ready",
                      "detail": f"Submission date: {draw.submission_date}."})

    # 7. Total submitted vs total invoiced sanity check
    total_invoiced = sum(i.total_due or 0 for i in invoices)
    total_submitted = sum(i.lender_submitted_amt or 0 for i in invoices if i.lender_submitted_amt)
    if total_submitted > 0 and total_submitted > total_invoiced * 1.5:
        warnings.append({
            "check": "amount_sanity",
            "label": "Amount Sanity Check",
            "status": "warning",
            "detail": f"Submitted amount (${total_submitted:,.2f}) is more than 150% of invoiced amount (${total_invoiced:,.2f}). Verify margins.",
        })
    elif total_submitted > 0:
        ready.append({"check": "amount_sanity", "label": "Amount Sanity Check", "status": "ready",
                      "detail": f"Submitted ${total_submitted:,.2f} against ${total_invoiced:,.2f} invoiced."})

    checklist = blocking + warnings + ready

    score = 100
    score -= len(blocking) * 25
    score -= len(warnings) * 10
    score = max(0, min(100, score))

    return {
        "draw_id": draw.id,
        "draw_number": draw.draw_number,
        "draw_status": draw.status,
        "readiness_score": score,
        "is_ready": len(blocking) == 0,
        "blocking_count": len(blocking),
        "warning_count": len(warnings),
        "ready_count": len(ready),
        "checklist": checklist,
        "summary": {
            "invoice_count": len(invoices),
            "total_invoiced": round(total_invoiced, 2),
            "total_submitted": round(total_submitted, 2),
        },
    }


# ─── Feature 5: Cash Flow Reality Simulator ──────────────────────────────────

def cashflow_scenarios(base_months: List[dict], project: Any,
                       delay_months: int = 0,
                       cost_inflation_pct: float = 0,
                       draw_delay_days: int = 0) -> dict:
    """Simulate cash flow under stress scenarios vs base case."""
    if not base_months:
        return {"base": [], "stressed": [], "summary": {}}

    stressed = []
    for i, m in enumerate(base_months):
        # Shift month forward by delay
        month_str = m["month"]
        try:
            dt = datetime.strptime(month_str + "-01", "%Y-%m-%d")
            stressed_dt = dt + timedelta(days=delay_months * 30)
            new_month = stressed_dt.strftime("%Y-%m")
        except Exception:
            new_month = month_str

        # Inflate spend
        inflated_spend = round(m["invoiced"] * (1 + cost_inflation_pct / 100), 2)
        inflated_projected = round(m["projected_spend"] * (1 + cost_inflation_pct / 100), 2)

        # Delay draw receipts by draw_delay_days
        draw_receipts = m["draw_receipts"]
        delayed_receipts = 0.0
        if draw_receipts > 0 and draw_delay_days > 0:
            # Push receipt to a later month
            delay_months_shift = draw_delay_days // 30
            try:
                dt = datetime.strptime(month_str + "-01", "%Y-%m-%d")
                delayed_dt = dt + timedelta(days=draw_delay_days)
                delayed_month = delayed_dt.strftime("%Y-%m")
                # For simplicity, set receipts to 0 this month; they'll appear in another month
                # We approximate by reducing this month's receipt by the delay factor
                delayed_receipts = 0.0
            except Exception:
                delayed_receipts = draw_receipts
        else:
            delayed_receipts = draw_receipts

        stressed_net = round(delayed_receipts - inflated_spend, 2)
        stressed.append({
            "month": new_month,
            "invoiced": inflated_spend,
            "paid": m["paid"],
            "draw_receipts": delayed_receipts,
            "projected_spend": inflated_projected,
            "net": stressed_net,
            "original_month": month_str,
        })

    # Compute cumulative for stressed
    cum = 0.0
    for m in stressed:
        cum = round(cum + m["net"], 2)
        m["cumulative"] = cum

    # Summary comparison
    base_total_spend = sum(m["invoiced"] for m in base_months)
    stressed_total_spend = sum(m["invoiced"] for m in stressed)
    base_total_receipts = sum(m["draw_receipts"] for m in base_months)
    stressed_total_receipts = sum(m["draw_receipts"] for m in stressed)
    base_final_position = base_months[-1].get("cumulative", 0) if base_months else 0
    stressed_final_position = stressed[-1].get("cumulative", 0) if stressed else 0

    # Find cash-negative months in stressed scenario
    cash_negative_months = [m["month"] for m in stressed if m.get("cumulative", 0) < 0]

    # Worst cash position
    worst_position = min((m.get("cumulative", 0) for m in stressed), default=0)

    return {
        "base": base_months,
        "stressed": stressed,
        "scenarios": {
            "delay_months": delay_months,
            "cost_inflation_pct": cost_inflation_pct,
            "draw_delay_days": draw_delay_days,
        },
        "summary": {
            "base_total_spend": round(base_total_spend, 2),
            "stressed_total_spend": round(stressed_total_spend, 2),
            "spend_increase": round(stressed_total_spend - base_total_spend, 2),
            "base_final_position": round(base_final_position, 2),
            "stressed_final_position": round(stressed_final_position, 2),
            "position_change": round(stressed_final_position - base_final_position, 2),
            "cash_negative_months": cash_negative_months,
            "worst_cash_position": round(worst_position, 2),
            "risk_level": (
                "critical" if worst_position < -500_000
                else "high" if worst_position < -100_000
                else "medium" if worst_position < 0
                else "low"
            ),
        },
    }


# ─── Feature 6: Subcontractor Risk Score ─────────────────────────────────────

def subcontractor_risk_scores(subcontractors: List[Any], invoices: List[Any],
                               change_orders: List[Any], lien_waivers: List[Any]) -> List[dict]:
    """Score each subcontractor 0–100 (lower = more risky) based on compliance and payment history."""
    today = _today()
    results = []

    for sub in subcontractors:
        score = 100
        risk_factors = []
        positive_factors = []
        sub_name_lower = (sub.name or "").lower()

        # 1. Insurance expiry
        if not sub.insurance_expiry:
            score -= 20
            risk_factors.append({"factor": "No insurance certificate on file", "impact": -20})
        elif sub.insurance_expiry < today:
            score -= 25
            risk_factors.append({"factor": f"Insurance expired {sub.insurance_expiry}", "impact": -25})
        elif _days_between(today, sub.insurance_expiry) is not None and _days_between(today, sub.insurance_expiry) <= 30:
            score -= 10
            risk_factors.append({"factor": f"Insurance expiring soon ({sub.insurance_expiry})", "impact": -10})
        else:
            positive_factors.append({"factor": "Insurance current", "impact": 0})

        # 2. WSIB expiry
        if not sub.wsib_expiry:
            score -= 15
            risk_factors.append({"factor": "No WSIB certificate on file", "impact": -15})
        elif sub.wsib_expiry < today:
            score -= 20
            risk_factors.append({"factor": f"WSIB expired {sub.wsib_expiry}", "impact": -20})
        else:
            positive_factors.append({"factor": "WSIB current", "impact": 0})

        # 3. Change orders — sub as issuer
        sub_cos = [co for co in change_orders
                   if (co.issued_by or "").lower() == sub_name_lower and co.amount > 0]
        if len(sub_cos) >= 3:
            score -= 15
            risk_factors.append({"factor": f"High change order frequency ({len(sub_cos)} COs)", "impact": -15})
        elif len(sub_cos) >= 2:
            score -= 8
            risk_factors.append({"factor": f"{len(sub_cos)} change orders issued", "impact": -8})
        elif len(sub_cos) == 0:
            positive_factors.append({"factor": "No change orders issued", "impact": 0})

        # 4. Lien waivers — unconditional waiver collected?
        has_unconditional = any(
            (w.vendor_name or "").lower() == sub_name_lower and w.waiver_type == "unconditional"
            for w in lien_waivers
        )
        has_conditional = any(
            (w.vendor_name or "").lower() == sub_name_lower and w.waiver_type == "conditional"
            for w in lien_waivers
        )
        if not has_unconditional and not has_conditional:
            score -= 10
            risk_factors.append({"factor": "No lien waivers on file", "impact": -10})
        elif not has_unconditional:
            score -= 5
            risk_factors.append({"factor": "Conditional waiver only (no unconditional)", "impact": -5})
        else:
            positive_factors.append({"factor": "Unconditional lien waiver collected", "impact": 0})

        # 5. Payment — invoices with outstanding balances
        sub_invoices = [i for i in invoices if (i.vendor_name or "").lower() == sub_name_lower]
        overdue_invs = []
        for inv in sub_invoices:
            due = inv.due_date or inv.invoice_date
            if due and inv.payment_status != "paid":
                days = _days_between(due, today) or 0
                if days > 60:
                    overdue_invs.append(inv)
        if overdue_invs:
            score -= 15
            risk_factors.append({"factor": f"{len(overdue_invs)} invoice(s) overdue >60 days", "impact": -15})

        # 6. Status
        if sub.status == "terminated":
            score -= 30
            risk_factors.append({"factor": "Subcontractor terminated", "impact": -30})
        elif sub.status == "complete":
            positive_factors.append({"factor": "Contract completed", "impact": 0})

        # 7. Contract value vs invoiced
        if sub.contract_value:
            sub_invoiced = sum(i.total_due or 0 for i in sub_invoices)
            if sub_invoiced > sub.contract_value * 1.15:
                overrun_pct = round((sub_invoiced / sub.contract_value - 1) * 100, 1)
                score -= 10
                risk_factors.append({"factor": f"Invoiced {overrun_pct}% over contract value", "impact": -10})

        score = max(0, min(100, score))
        risk_level = (
            "critical" if score < 40
            else "high" if score < 60
            else "medium" if score < 75
            else "low"
        )

        results.append({
            "subcontractor_id": sub.id,
            "name": sub.name,
            "trade": sub.trade,
            "status": sub.status,
            "risk_score": score,
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "positive_factors": positive_factors,
            "contract_value": sub.contract_value,
            "insurance_expiry": sub.insurance_expiry,
            "wsib_expiry": sub.wsib_expiry,
            "summary": (
                f"High risk — {risk_factors[0]['factor']}" if risk_level in ("critical", "high") and risk_factors
                else f"Medium risk — monitor {len(risk_factors)} factor(s)" if risk_level == "medium"
                else "Low risk — all compliance checks passing"
            ),
        })

    results.sort(key=lambda r: r["risk_score"])
    return results


# ─── Feature 7: Lender Behavior Model ────────────────────────────────────────

def lender_insights(draws: List[Any], invoices: List[Any], lien_waivers: List[Any],
                    documents: List[Any]) -> dict:
    """Detect common lender rejection patterns and submission optimization tips."""
    insights = []
    tips = []
    patterns = []

    # Pattern 1: Invoices rejected by lender
    rejected_invs = [i for i in invoices if i.lender_status == "rejected"]
    if rejected_invs:
        total_rejected = sum(i.lender_submitted_amt or i.total_due or 0 for i in rejected_invs)
        patterns.append({
            "pattern": "lender_rejections",
            "title": f"Lender Rejected {len(rejected_invs)} Invoice(s)",
            "detail": f"${total_rejected:,.2f} has been rejected. Review each invoice for missing documentation or margin discrepancies.",
            "severity": "high",
            "items": [{"id": i.id, "vendor": i.vendor_name, "submitted": i.lender_submitted_amt} for i in rejected_invs[:5]],
        })

    # Pattern 2: Partial approvals (approved < submitted)
    partial_invs = [i for i in invoices
                    if i.lender_approved_amt is not None
                    and i.lender_submitted_amt is not None
                    and i.lender_approved_amt < i.lender_submitted_amt * 0.95]
    if partial_invs:
        total_shortfall = sum((i.lender_submitted_amt or 0) - (i.lender_approved_amt or 0) for i in partial_invs)
        patterns.append({
            "pattern": "partial_approvals",
            "title": f"{len(partial_invs)} Invoice(s) Partially Approved",
            "detail": f"Lender approved less than 95% of submitted amount on {len(partial_invs)} invoice(s). Total shortfall: ${total_shortfall:,.2f}. May indicate ineligible cost types or missing backup.",
            "severity": "warning",
            "shortfall": round(total_shortfall, 2),
        })

    # Pattern 3: Draws submitted without complete lien waivers
    for draw in draws:
        if draw.status in ("submitted", "approved", "funded"):
            draw_invs = [i for i in invoices if i.draw_id == draw.id]
            vendors = {(i.vendor_name or "").lower() for i in draw_invs if i.vendor_name}
            covered = {(w.vendor_name or "").lower() for w in lien_waivers
                       if w.draw_id == draw.id and w.vendor_name}
            missing = vendors - covered
            if missing:
                patterns.append({
                    "pattern": "draw_missing_waivers",
                    "title": f"Draw {draw.draw_number}: Submitted Without Complete Lien Waivers",
                    "detail": f"{len(missing)} vendor(s) had no lien waiver when draw was submitted. Lenders commonly reject or hold draws for this reason.",
                    "severity": "warning",
                    "draw_number": draw.draw_number,
                    "missing_vendors": list(missing)[:5],
                })

    # Pattern 4: Average approval rate across all draws
    approved_invs = [i for i in invoices if i.lender_status == "approved" and i.lender_approved_amt]
    submitted_invs = [i for i in invoices if i.lender_submitted_amt]
    if submitted_invs:
        total_sub = sum(i.lender_submitted_amt or 0 for i in submitted_invs)
        total_app = sum(i.lender_approved_amt or 0 for i in approved_invs)
        approval_rate = round(total_app / total_sub * 100, 1) if total_sub > 0 else 0
        if approval_rate < 85:
            tips.append({
                "tip": "low_approval_rate",
                "title": f"Approval Rate: {approval_rate}%",
                "detail": "Overall lender approval rate is below 85%. Review rejected and partially approved invoices to identify recurring issues.",
                "severity": "warning",
            })
        else:
            tips.append({
                "tip": "approval_rate",
                "title": f"Approval Rate: {approval_rate}%",
                "detail": f"${total_app:,.2f} approved of ${total_sub:,.2f} submitted.",
                "severity": "info",
            })

    # Pattern 5: Invoices not yet submitted to lender
    unsubmitted = [i for i in invoices if i.lender_submitted_amt is None and i.approval_status == "approved"]
    if unsubmitted:
        total_unsubmitted = sum(i.total_due or 0 for i in unsubmitted)
        tips.append({
            "tip": "unsubmitted_invoices",
            "title": f"{len(unsubmitted)} Approved Invoice(s) Not Yet Submitted",
            "detail": f"${total_unsubmitted:,.2f} in approved invoices have no lender submitted amount. Add them to a draw to recover costs.",
            "severity": "info",
        })

    # Tips for draw timing
    if len(draws) > 1:
        submitted_draws = [d for d in draws if d.submission_date]
        if len(submitted_draws) >= 2:
            # Check interval between draws
            dates = sorted(d.submission_date for d in submitted_draws)
            intervals = [_days_between(dates[i], dates[i+1]) for i in range(len(dates)-1)]
            intervals = [x for x in intervals if x is not None]
            if intervals:
                avg_interval = sum(intervals) / len(intervals)
                if avg_interval > 60:
                    tips.append({
                        "tip": "draw_frequency",
                        "title": f"Draw Submissions Averaging {avg_interval:.0f} Days Apart",
                        "detail": "Submitting draws more frequently (every 30 days) improves cash flow and reduces lender exposure risk.",
                        "severity": "info",
                    })

    return {
        "patterns": patterns,
        "tips": tips,
        "pattern_count": len(patterns),
        "tip_count": len(tips),
        "total_submitted": round(sum(i.lender_submitted_amt or 0 for i in invoices if i.lender_submitted_amt), 2),
        "total_approved": round(sum(i.lender_approved_amt or 0 for i in invoices if i.lender_approved_amt), 2),
        "total_rejected": round(sum(i.lender_submitted_amt or 0 for i in rejected_invs), 2),
    }


# ─── Feature 8: Draw Approval Probability Score ──────────────────────────────

def draw_approval_probability(draw: Any, invoices: List[Any], categories: List[Any],
                               change_orders: List[Any], lien_waivers: List[Any],
                               allocations_by_cat: Dict[int, float]) -> dict:
    """Score each invoice 0–100 on lender approval likelihood before submission.
    Lower score = higher risk of rejection or partial approval."""
    today = _today()
    cat_map = {c.id: c for c in categories}
    approved_co_by_cat: Dict[int, float] = {}
    for co in change_orders:
        if co.status == "approved" and co.category_id:
            approved_co_by_cat[co.category_id] = approved_co_by_cat.get(co.category_id, 0.0) + co.amount

    invoice_scores = []
    draw_score_sum = 0.0

    for inv in invoices:
        score = 100
        risk_flags = []
        good_flags = []

        # 1. Internal approval
        if inv.approval_status == "rejected":
            score -= 40
            risk_flags.append({"flag": "Rejected internally", "impact": -40})
        elif inv.approval_status == "pending":
            score -= 20
            risk_flags.append({"flag": "Pending internal approval", "impact": -20})
        else:
            good_flags.append("Internally approved")

        # 2. Lender submitted amount set
        if inv.lender_submitted_amt is None:
            score -= 15
            risk_flags.append({"flag": "No lender submitted amount set", "impact": -15})
        else:
            good_flags.append("Submitted amount configured")

        # 3. Category allocation exists
        alloc_count = len(getattr(inv, '_allocs', []) or [])
        if alloc_count == 0:
            score -= 15
            risk_flags.append({"flag": "Not allocated to a cost category", "impact": -15})
        else:
            good_flags.append("Allocated to cost category")

        # 4. Budget burn — is this category already over budget?
        primary_cat_id = None
        for a in (getattr(inv, '_allocs', []) or []):
            primary_cat_id = a.category_id
            break
        if primary_cat_id and primary_cat_id in cat_map:
            cat = cat_map[primary_cat_id]
            revised_budget = cat.budget + approved_co_by_cat.get(cat.id, 0.0)
            invoiced = allocations_by_cat.get(cat.id, 0.0)
            if revised_budget > 0:
                pct = invoiced / revised_budget * 100
                if pct > 110:
                    score -= 20
                    risk_flags.append({"flag": f"Category '{cat.name}' is {pct:.0f}% over budget — lenders may reject", "impact": -20})
                elif pct > 95:
                    score -= 10
                    risk_flags.append({"flag": f"Category '{cat.name}' is {pct:.0f}% of budget — near limit", "impact": -10})
                else:
                    good_flags.append(f"Category '{cat.name}' within budget ({pct:.0f}%)")

        # 5. Holdback applied
        if (inv.holdback_pct or 0) == 0 and not getattr(inv, 'is_payroll', False):
            score -= 5
            risk_flags.append({"flag": "No holdback applied (lender may require 10%)", "impact": -5})
        else:
            good_flags.append("Holdback applied")

        # 6. Tax treatment set
        if inv.billing_type is None and not getattr(inv, 'is_payroll', False):
            score -= 5
            risk_flags.append({"flag": "Billing type not set (direct/pass-through unclear)", "impact": -5})

        # 7. Lien waiver for this vendor
        vendor_lower = (inv.vendor_name or "").lower()
        has_waiver = any((w.vendor_name or "").lower() == vendor_lower for w in lien_waivers if w.vendor_name)
        if not has_waiver and not getattr(inv, 'is_payroll', False):
            score -= 5
            risk_flags.append({"flag": "No lien waiver on file for this vendor", "impact": -5})
        elif has_waiver:
            good_flags.append("Lien waiver on file")

        # 8. Invoice age (very old invoices questioned by lenders)
        inv_date = inv.invoice_date
        if inv_date:
            days_old = _days_between(inv_date, today) or 0
            if days_old > 180:
                score -= 10
                risk_flags.append({"flag": f"Invoice is {days_old} days old — lenders may question inclusion", "impact": -10})
            elif days_old > 90:
                score -= 5
                risk_flags.append({"flag": f"Invoice is {days_old} days old", "impact": -5})

        score = max(0, min(100, score))
        risk_level = "critical" if score < 40 else "high" if score < 60 else "medium" if score < 75 else "low"
        draw_score_sum += score

        invoice_scores.append({
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "vendor": inv.vendor_name,
            "amount": inv.total_due,
            "submitted": inv.lender_submitted_amt,
            "approval_score": score,
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "good_flags": good_flags,
            "approval_status": inv.approval_status,
            "lender_status": inv.lender_status,
        })

    invoice_scores.sort(key=lambda x: x["approval_score"])

    draw_avg = round(draw_score_sum / len(invoices), 1) if invoices else 0
    draw_probability = draw_avg  # 0-100 scale

    prediction = (
        "HIGH probability of full approval" if draw_probability >= 80
        else "LIKELY to be partially approved — review flagged invoices" if draw_probability >= 60
        else "MODERATE rejection risk — address flags before submission" if draw_probability >= 40
        else "HIGH rejection risk — significant issues require resolution"
    )

    high_risk_count = sum(1 for s in invoice_scores if s["risk_level"] in ("critical", "high"))
    total_at_risk = sum(s["submitted"] or s["amount"] or 0
                        for s in invoice_scores if s["risk_level"] in ("critical", "high"))

    return {
        "draw_id": draw.id,
        "draw_number": draw.draw_number,
        "approval_probability": draw_probability,
        "prediction": prediction,
        "invoice_count": len(invoices),
        "high_risk_count": high_risk_count,
        "total_at_risk": round(total_at_risk, 2),
        "invoices": invoice_scores,
    }


# ─── Feature 9: Closeout Readiness Agent ─────────────────────────────────────

def closeout_readiness(project: Any, invoices: List[Any], milestones: List[Any],
                        lien_waivers: List[Any], documents: List[Any],
                        subcontractors: List[Any], draws: List[Any],
                        claims: List[Any]) -> dict:
    """Real-time project closeout checklist — what's done and what's still needed."""
    today = _today()
    checklist = []
    score_points = 0
    total_points = 0

    def _add(category: str, label: str, status: str, detail: str, points: int, action: str = ""):
        nonlocal score_points, total_points
        total_points += points
        if status == "done":
            score_points += points
        checklist.append({
            "category": category,
            "label": label,
            "status": status,        # done | pending | warning | blocking
            "detail": detail,
            "action": action,
            "points": points,
        })

    # ── Invoices ──────────────────────────────────────────────────────────────
    unpaid = [i for i in invoices if i.payment_status != "paid"]
    unallocated = [i for i in invoices if len(getattr(i, '_allocs', []) or []) == 0]
    pending_approval = [i for i in invoices if i.approval_status == "pending"]

    _add("Invoices", "All Invoices Paid",
         "done" if not unpaid else "blocking",
         f"{len(unpaid)} unpaid invoice(s) outstanding." if unpaid else "All invoices paid.",
         15, f"Pay {len(unpaid)} outstanding invoice(s)." if unpaid else "")

    _add("Invoices", "All Invoices Allocated",
         "done" if not unallocated else "warning",
         f"{len(unallocated)} invoice(s) not allocated to cost categories." if unallocated else "All invoices allocated.",
         5, "Allocate unallocated invoices." if unallocated else "")

    _add("Invoices", "All Invoices Approved",
         "done" if not pending_approval else "warning",
         f"{len(pending_approval)} invoice(s) still pending approval." if pending_approval else "All invoices approved.",
         5, "Approve or reject pending invoices." if pending_approval else "")

    # ── Holdback ──────────────────────────────────────────────────────────────
    unreleased_hb = [i for i in invoices
                     if (i.holdback_pct or 0) > 0 and not i.holdback_released]
    _add("Holdback", "All Holdback Released",
         "done" if not unreleased_hb else "pending",
         f"${sum(round((i.subtotal or i.total_due or 0)*(i.holdback_pct or 0)/100,2) for i in unreleased_hb):,.2f} holdback still unreleased on {len(unreleased_hb)} invoice(s)." if unreleased_hb else "All holdback released.",
         15, "Release holdback on completed work." if unreleased_hb else "")

    # ── Lien Waivers ──────────────────────────────────────────────────────────
    paid_vendors = {(i.vendor_name or "").lower() for i in invoices
                    if i.payment_status == "paid" and i.vendor_name}
    unconditional_vendors = {(w.vendor_name or "").lower() for w in lien_waivers
                              if w.waiver_type == "unconditional" and w.vendor_name}
    missing_unconditional = paid_vendors - unconditional_vendors

    _add("Lien Waivers", "Unconditional Lien Waivers — All Paid Vendors",
         "done" if not missing_unconditional else "blocking",
         f"{len(missing_unconditional)} vendor(s) paid but missing unconditional lien waiver." if missing_unconditional else "Unconditional waivers collected from all paid vendors.",
         20, f"Collect unconditional waivers from: {', '.join(list(missing_unconditional)[:3])}{'...' if len(missing_unconditional)>3 else ''}." if missing_unconditional else "")

    # ── Draws ─────────────────────────────────────────────────────────────────
    draft_draws = [d for d in draws if d.status == "draft"]
    unfunded_draws = [d for d in draws if d.status in ("draft", "submitted", "approved")]

    _add("Draws", "All Draws Funded",
         "done" if not unfunded_draws else "pending",
         f"{len(unfunded_draws)} draw(s) not yet funded." if unfunded_draws else "All draws funded by lender.",
         10, "Follow up with lender on outstanding draws." if unfunded_draws else "")

    # ── Milestones ────────────────────────────────────────────────────────────
    incomplete_ms = [m for m in milestones if m.status not in ("complete",) and m.pct_complete < 100]
    _add("Milestones", "All Milestones Complete",
         "done" if not incomplete_ms else "pending",
         f"{len(incomplete_ms)} milestone(s) not yet marked complete." if incomplete_ms else "All milestones complete.",
         10, "Mark remaining milestones complete." if incomplete_ms else "")

    # ── Documents ─────────────────────────────────────────────────────────────
    doc_types_present = {d.doc_type for d in documents}
    required_types = {"permit", "contract"}
    recommended_types = {"drawing", "report"}  # as-builts, final reports

    missing_required = required_types - doc_types_present
    missing_recommended = recommended_types - doc_types_present

    _add("Documents", "Required Documents on File (Permits, Contracts)",
         "done" if not missing_required else "warning",
         f"Missing document type(s): {', '.join(missing_required)}." if missing_required else "All required document types on file.",
         10, f"Upload {', '.join(missing_required)}." if missing_required else "")

    _add("Documents", "As-Builts and Final Reports",
         "done" if not missing_recommended else "warning",
         f"Recommended documents missing: {', '.join(missing_recommended)}." if missing_recommended else "As-builts and reports on file.",
         5, f"Upload {', '.join(missing_recommended)}." if missing_recommended else "")

    # ── Subcontractors ────────────────────────────────────────────────────────
    active_subs = [s for s in subcontractors if s.status == "active"]
    _add("Subcontractors", "All Subcontract Work Complete",
         "done" if not active_subs else "pending",
         f"{len(active_subs)} subcontractor(s) still marked active." if active_subs else "All subcontracts marked complete.",
         5, "Mark completed subcontracts as 'complete'." if active_subs else "")

    # ── Claims ────────────────────────────────────────────────────────────────
    open_claims = [c for c in claims if c.status in ("draft", "submitted")]
    _add("Claims", "All Government Claims Received",
         "done" if not open_claims else "pending",
         f"{len(open_claims)} government claim(s) not yet received/approved." if open_claims else "All government claims received.",
         5, "Follow up on outstanding claims." if open_claims else "")

    # ── Final project dates ───────────────────────────────────────────────────
    if project.end_date:
        days_to_end = _days_between(today, project.end_date)
        if days_to_end is not None:
            if days_to_end < 0:
                _add("Schedule", "Project End Date",
                     "warning",
                     f"Project end date was {abs(days_to_end)} days ago ({project.end_date}). Update end date or mark project complete.",
                     5, "Update project end date.")
            elif days_to_end <= 30:
                _add("Schedule", "Project End Date",
                     "pending",
                     f"Project end date is {days_to_end} days away ({project.end_date}). Ensure all closeout tasks are addressed.",
                     5, "Complete all closeout checklist items.")
            else:
                _add("Schedule", "Project End Date",
                     "done",
                     f"Project end date: {project.end_date} ({days_to_end} days remaining).",
                     5)

    # ── Compute completion percentage ─────────────────────────────────────────
    pct_complete = round(score_points / total_points * 100, 1) if total_points else 0
    blocking = [c for c in checklist if c["status"] == "blocking"]
    pending = [c for c in checklist if c["status"] in ("pending", "warning")]
    done = [c for c in checklist if c["status"] == "done"]

    return {
        "pct_complete": pct_complete,
        "is_ready": pct_complete >= 90 and not blocking,
        "blocking_count": len(blocking),
        "pending_count": len(pending),
        "done_count": len(done),
        "total_items": len(checklist),
        "checklist": checklist,
        "categories": list({c["category"] for c in checklist}),
    }


# ─── Feature 10: Government Claim Optimizer ──────────────────────────────────

# Categories that are typically non-eligible for government grants/subsidies
_NON_ELIGIBLE_KEYWORDS = {
    "contingency", "legal", "financing", "interest", "marketing",
    "insurance", "bond", "admin", "overhead", "profit",
}

def govt_claim_optimizer(invoices: List[Any], payroll_entries: List[Any],
                          categories: List[Any]) -> dict:
    """Separate project costs into lender-eligible, provincial-eligible, federal-eligible,
    and non-eligible buckets. Suggest optimal submission order to maximize recovery."""
    cat_map = {c.id: c for c in categories}
    today = _today()

    lender_eligible = []
    provincial_eligible = []
    federal_eligible = []
    non_eligible = []
    already_assigned = []

    total_lender = 0.0
    total_prov = 0.0
    total_fed = 0.0
    total_non = 0.0

    for inv in invoices:
        # Get primary category name for eligibility check
        primary_cat = None
        for a in (getattr(inv, '_allocs', []) or []):
            c = cat_map.get(a.category_id)
            if c:
                primary_cat = c.name.lower()
                break

        amount = inv.lender_submitted_amt or inv.subtotal or inv.total_due or 0

        # Already assigned to a draw/claim
        assigned_to = []
        if inv.draw_id:
            assigned_to.append(f"Draw #{inv.draw_id}")
        if inv.provincial_claim_id:
            assigned_to.append(f"Prov Claim #{inv.provincial_claim_id}")
        if inv.federal_claim_id:
            assigned_to.append(f"Fed Claim #{inv.federal_claim_id}")

        inv_record = {
            "invoice_id": inv.id,
            "invoice_number": inv.invoice_number,
            "vendor": inv.vendor_name,
            "amount": round(amount, 2),
            "category": primary_cat or "unallocated",
            "billing_type": inv.billing_type,
            "currency": inv.currency or "CAD",
            "assigned_to": assigned_to,
        }

        # Check eligibility
        is_non_eligible = primary_cat and any(kw in primary_cat for kw in _NON_ELIGIBLE_KEYWORDS)

        if is_non_eligible:
            non_eligible.append({**inv_record, "reason": "Category typically ineligible for government claims"})
            total_non += amount
        elif assigned_to:
            already_assigned.append({**inv_record, "note": ", ".join(assigned_to)})
        else:
            # Determine eligible buckets
            lender_eligible.append({**inv_record, "bucket": "lender"})
            total_lender += amount

            # Government eligibility — tax portion excluded, direct eligible
            govt_amount = inv.subtotal or (inv.total_due or 0)  # govt gets pre-tax amount
            if inv.billing_type in ("direct", None):
                provincial_eligible.append({**inv_record, "amount": round(govt_amount, 2), "bucket": "provincial"})
                total_prov += govt_amount
                federal_eligible.append({**inv_record, "amount": round(govt_amount, 2), "bucket": "federal"})
                total_fed += govt_amount

    # Payroll — separate lender vs govt billable
    payroll_lender_unsubmitted = []
    payroll_prov_unsubmitted = []
    payroll_total_lender = 0.0
    payroll_total_prov = 0.0

    for p in payroll_entries:
        if p.lender_billable and p.lender_status == "pending":
            payroll_lender_unsubmitted.append({
                "type": "payroll",
                "employee": p.employee_name or p.company_name or "Unknown",
                "period": f"{p.pay_period_start} to {p.pay_period_end}" if p.pay_period_start else "—",
                "amount": round(p.lender_billable or 0, 2),
                "bucket": "lender",
            })
            payroll_total_lender += p.lender_billable or 0
        if p.govt_billable and p.govt_status == "pending":
            payroll_prov_unsubmitted.append({
                "type": "payroll",
                "employee": p.employee_name or p.company_name or "Unknown",
                "period": f"{p.pay_period_start} to {p.pay_period_end}" if p.pay_period_start else "—",
                "amount": round(p.govt_billable or 0, 2),
                "bucket": "provincial",
            })
            payroll_total_prov += p.govt_billable or 0

    # Recovery gap — costs assigned to draw but not to claims
    draw_only = [i for i in already_assigned
                 if any("Draw" in a for a in i["assigned_to"])
                 and not any("Claim" in a for a in i["assigned_to"])]
    recovery_gap = sum(i["amount"] for i in draw_only)

    # Submission order recommendation
    recommendations = []
    if lender_eligible:
        recommendations.append({
            "order": 1,
            "action": "Submit to lender draw first",
            "reason": "Lender approval typically faster than government. Improves cash flow.",
            "count": len(lender_eligible),
            "amount": round(total_lender + payroll_total_lender, 2),
        })
    if provincial_eligible:
        recommendations.append({
            "order": 2,
            "action": "Submit to provincial claim second",
            "reason": "Provincial claims typically process faster than federal.",
            "count": len(provincial_eligible),
            "amount": round(total_prov + payroll_total_prov, 2),
        })
    if federal_eligible:
        recommendations.append({
            "order": 3,
            "action": "Submit to federal claim last",
            "reason": "Federal approvals typically slowest. Bundle with provincial-approved amounts.",
            "count": len(federal_eligible),
            "amount": round(total_fed, 2),
        })
    if recovery_gap > 0:
        recommendations.append({
            "order": 0,
            "action": f"Claim recovery gap: ${recovery_gap:,.2f} in draw-assigned invoices not yet on any government claim",
            "reason": "These invoices were submitted to lender but may also be eligible for government claims.",
            "count": len(draw_only),
            "amount": round(recovery_gap, 2),
        })

    max_recovery = round(total_lender + payroll_total_lender + total_prov + payroll_total_prov + total_fed, 2)

    return {
        "lender_eligible": lender_eligible,
        "provincial_eligible": provincial_eligible,
        "federal_eligible": federal_eligible,
        "non_eligible": non_eligible,
        "already_assigned": already_assigned,
        "payroll_lender": payroll_lender_unsubmitted,
        "payroll_provincial": payroll_prov_unsubmitted,
        "totals": {
            "lender": round(total_lender + payroll_total_lender, 2),
            "provincial": round(total_prov + payroll_total_prov, 2),
            "federal": round(total_fed, 2),
            "non_eligible": round(total_non, 2),
            "recovery_gap": round(recovery_gap, 2),
            "max_potential_recovery": max_recovery,
        },
        "recommendations": sorted(recommendations, key=lambda r: r["order"]),
        "unassigned_count": len(lender_eligible),
    }


# ─── Feature 11: Cost Consultant in a Box ────────────────────────────────────

def cost_consultant_commentary(project: Any, dashboard: dict, db: Any) -> dict:
    """Use Gemini to generate a professional monthly cost consultant commentary.
    Falls back to a data-driven template if no API key is available."""
    from .gemini import _env_keys
    from ..models import GeminiApiKey

    api_keys = _env_keys()
    if not api_keys:
        db_keys = db.query(GeminiApiKey).filter(GeminiApiKey.is_active == True).order_by(GeminiApiKey.priority).all()
        api_keys = [k.key_value for k in db_keys]

    total_budget  = dashboard.get("total_revised_budget", 0) or dashboard.get("total_budget", 0)
    total_invoiced = dashboard.get("total_invoiced", 0)
    total_remaining = dashboard.get("total_remaining", 0)
    pct_burn = round(total_invoiced / total_budget * 100, 1) if total_budget else 0
    holdback = (dashboard.get("holdback") or {}).get("held", 0)
    total_co = dashboard.get("total_co_adjustment", 0)
    unallocated = dashboard.get("unallocated_invoices", 0)
    approval = dashboard.get("approval") or {}

    # Build per-category context
    cat_data = dashboard.get("categories") or []
    at_risk_cats = [c for c in cat_data if c.get("pct_burn", 0) >= 85]
    over_budget_cats = [c for c in cat_data if c.get("invoiced", 0) > c.get("revised_budget", 0)]

    # Timeline progress
    timeline_pct = None
    if project.start_date and project.end_date:
        total_days = _days_between(project.start_date, project.end_date)
        elapsed = _days_between(project.start_date, _today())
        if total_days and total_days > 0 and elapsed is not None:
            timeline_pct = max(0.0, min(100.0, round(elapsed / total_days * 100, 1)))

    context = {
        "project_name": project.name,
        "total_budget": total_budget,
        "total_invoiced": total_invoiced,
        "pct_burn": pct_burn,
        "total_remaining": total_remaining,
        "total_co_adjustments": total_co,
        "holdback_held": holdback,
        "timeline_pct": timeline_pct,
        "unallocated_invoices": unallocated,
        "approval_pending": approval.get("pending", 0),
        "at_risk_categories": [{"name": c["name"], "pct_burn": c.get("pct_burn"), "remaining": c.get("remaining")} for c in at_risk_cats],
        "over_budget_categories": [{"name": c["name"], "overrun": round(c.get("invoiced",0) - c.get("revised_budget",0), 2)} for c in over_budget_cats],
    }

    if api_keys:
        try:
            import google.generativeai as genai
            import json as _json
            genai.configure(api_key=api_keys[0])
            model = genai.GenerativeModel("gemini-1.5-flash")
            prompt = f"""You are a senior construction cost consultant writing a monthly project status commentary for a Canadian real estate developer or infrastructure builder.

Project data:
{_json.dumps(context, indent=2)}

Write a professional cost consultant commentary with exactly these 4 sections. Be specific, use the numbers, be direct about risks. Maximum 300 words total.

FORMAT YOUR RESPONSE AS JSON with these exact keys:
{{
  "executive_summary": "1-2 sentence executive summary of project financial health.",
  "budget_status": "Paragraph on budget vs actual, burn rate, categories at risk, change orders.",
  "key_risks": "Paragraph on the top 2-3 financial risks facing the project right now.",
  "recommended_actions": "Bulleted list of 3-5 specific recommended actions (use \\n between items)."
}}

Use Canadian construction finance terminology. Be direct, not generic."""

            resp = model.generate_content(prompt)
            text = resp.text.strip()
            if text.startswith("```"):
                text = text.split("```")[1]
                if text.startswith("json"):
                    text = text[4:]
            sections = _json.loads(text.strip())
            sections["generated_by"] = "gemini"
            sections["generated_at"] = _today()
            sections["data"] = context
            return sections
        except Exception as e:
            logger.warning("Gemini cost consultant failed: %s", e)

    # Template fallback
    burn_status = "on track" if (timeline_pct is None or abs(pct_burn - (timeline_pct or 0)) <= 10) else ("running ahead of schedule" if pct_burn > (timeline_pct or 0) else "running behind schedule")
    risk_bullets = []
    if over_budget_cats:
        risk_bullets.append(f"Budget overrun: {', '.join(c['name'] for c in over_budget_cats)} exceeded approved budget.")
    if at_risk_cats:
        risk_bullets.append(f"Near-limit categories: {', '.join(c['name'] for c in at_risk_cats[:2])} at ≥85% budget burn.")
    if unallocated > 0:
        risk_bullets.append(f"{unallocated} invoice(s) not allocated to cost categories — budget tracking incomplete.")
    if total_co > 0:
        risk_bullets.append(f"Change orders have increased total budget by ${total_co:,.2f} — monitor for further scope creep.")
    if not risk_bullets:
        risk_bullets.append("No material budget risks identified at this time.")

    actions = [
        f"Review and resolve {approval.get('pending',0)} pending invoice approval(s)." if approval.get('pending',0) > 0 else None,
        f"Allocate {unallocated} unallocated invoice(s) to cost categories." if unallocated > 0 else None,
        f"Issue change orders for over-budget categories: {', '.join(c['name'] for c in over_budget_cats)}." if over_budget_cats else None,
        f"Release holdback on eligible invoices (${holdback:,.2f} currently held)." if holdback > 0 else None,
        "Submit next draw package to lender to maintain cash flow." if pct_burn > 40 else None,
    ]
    actions = [a for a in actions if a][:5]

    return {
        "executive_summary": f"{project.name} is {pct_burn:.1f}% through its budget with {(str(timeline_pct)+'%') if timeline_pct else 'N/A'} of the project timeline elapsed. Financial health is {'concerning' if over_budget_cats else 'acceptable' if at_risk_cats else 'healthy'}.",
        "budget_status": f"Total budget of ${total_budget:,.2f} CAD has ${total_invoiced:,.2f} ({pct_burn:.1f}%) invoiced to date, leaving ${total_remaining:,.2f} remaining. The project is {burn_status}. Change orders total ${total_co:,.2f}. Holdback held: ${holdback:,.2f}.",
        "key_risks": " ".join(risk_bullets),
        "recommended_actions": "\n".join(f"• {a}" for a in (actions or ["No immediate actions required."])),
        "generated_by": "template",
        "generated_at": _today(),
        "data": context,
    }


# ─── Feature 12: Change Order Early Warning Radar ────────────────────────────

# Keywords in invoice descriptions that often precede formal change orders
_CO_SIGNAL_KEYWORDS = [
    "extra", "additional", "unforeseen", "changed", "revised", "scope change",
    "added", "new requirement", "out of scope", "variation", "modification",
    "directed", "instruction", "site condition", "differing", "acceleration",
    "delay", "disruption", "rework", "remediation", "change in",
]

def co_early_warning(invoices: List[Any], categories: List[Any],
                      change_orders: List[Any], committed_costs: List[Any],
                      allocations_by_cat: Dict[int, float]) -> dict:
    """Detect likely change orders before they are formally issued by reading
    invoice descriptions, budget drift, and CO velocity."""
    today = _today()
    cat_map = {c.id: c for c in categories}
    signals = []

    # Approved CO amounts by category
    approved_co_by_cat: Dict[int, float] = {}
    for co in change_orders:
        if co.status == "approved" and co.category_id:
            approved_co_by_cat[co.category_id] = approved_co_by_cat.get(co.category_id, 0.0) + co.amount

    # CO velocity — is the rate of new COs increasing?
    recent_cos = [co for co in change_orders if co.date and _days_between(co.date, today) is not None and _days_between(co.date, today) <= 30]
    older_cos  = [co for co in change_orders if co.date and _days_between(co.date, today) is not None and 30 < _days_between(co.date, today) <= 60]
    co_velocity_signal = len(recent_cos) > len(older_cos) and len(recent_cos) > 0

    if co_velocity_signal:
        signals.append({
            "type": "co_velocity",
            "severity": "warning",
            "title": f"Change Order Rate Accelerating — {len(recent_cos)} in last 30 days vs {len(older_cos)} in prior 30",
            "detail": "An increasing change order rate often indicates unresolved scope disputes. Review open COs and pending invoices.",
            "category": None,
            "amount_at_risk": round(sum(co.amount for co in recent_cos if co.amount > 0), 2),
        })

    # Invoice description keyword signals
    invoice_keyword_hits = []
    for inv in invoices:
        if inv.approval_status == "approved":
            continue  # already processed
        description = ""
        if inv.extracted_data and isinstance(inv.extracted_data, dict):
            description = str(inv.extracted_data.get("description", "") or "")
            items = inv.extracted_data.get("line_items") or inv.extracted_data.get("items") or []
            if isinstance(items, list):
                description += " ".join(str(i) for i in items)
        description = description.lower()
        matched = [kw for kw in _CO_SIGNAL_KEYWORDS if kw in description]
        if matched:
            invoice_keyword_hits.append({
                "invoice_id": inv.id,
                "vendor": inv.vendor_name,
                "amount": inv.total_due,
                "matched_keywords": matched[:3],
            })

    if invoice_keyword_hits:
        total_at_risk = sum(h["amount"] or 0 for h in invoice_keyword_hits)
        signals.append({
            "type": "invoice_description_keywords",
            "severity": "warning",
            "title": f"{len(invoice_keyword_hits)} Invoice(s) Contain Change Order Keywords",
            "detail": f"Invoice descriptions contain terms like 'extra work', 'scope change', or 'unforeseen'. Total value: ${total_at_risk:,.2f}. These may represent undocumented change orders.",
            "category": None,
            "amount_at_risk": round(total_at_risk, 2),
            "items": invoice_keyword_hits[:5],
        })

    # Budget drift — categories spending faster than timeline suggests
    for cat in categories:
        budget = cat.budget + approved_co_by_cat.get(cat.id, 0.0)
        invoiced = allocations_by_cat.get(cat.id, 0.0)
        if budget <= 0 or invoiced <= 0:
            continue
        pct = invoiced / budget * 100

        # Committed cost gap: contracted more than invoiced — may be accelerating
        committed_for_cat = sum(cc.contract_amount for cc in committed_costs
                                 if cc.category_id == cat.id and cc.status == "active")
        invoiced_committed = sum(cc.invoiced_to_date or 0 for cc in committed_costs
                                  if cc.category_id == cat.id and cc.status == "active")
        committed_burn = round(invoiced_committed / committed_for_cat * 100, 1) if committed_for_cat > 0 else 0

        if pct >= 80 and not any(co.category_id == cat.id for co in change_orders if co.status in ("pending", "approved")):
            signals.append({
                "type": "budget_drift_no_co",
                "severity": "high" if pct >= 95 else "warning",
                "title": f"'{cat.name}' at {pct:.0f}% budget with no pending CO",
                "detail": f"This category is {pct:.0f}% through its ${budget:,.2f} budget but has no pending or approved change order. If additional work is required, a CO should be issued before further invoicing.",
                "category": cat.name,
                "amount_at_risk": round(budget - invoiced, 2),
            })

        if committed_for_cat > budget * 1.1:
            overcommit = committed_for_cat - budget
            signals.append({
                "type": "over_committed",
                "severity": "warning",
                "title": f"'{cat.name}' is over-committed by ${overcommit:,.2f}",
                "detail": f"Committed contracts (${committed_for_cat:,.2f}) exceed the category budget (${budget:,.2f}) by ${overcommit:,.2f}. A change order is likely required.",
                "category": cat.name,
                "amount_at_risk": round(overcommit, 2),
            })

    # Pending COs — flag high-value ones sitting unapproved
    pending_cos = [co for co in change_orders if co.status == "pending"]
    if pending_cos:
        total_pending = sum(co.amount for co in pending_cos if co.amount > 0)
        signals.append({
            "type": "pending_change_orders",
            "severity": "info",
            "title": f"{len(pending_cos)} Change Order(s) Pending Approval — ${total_pending:,.2f}",
            "detail": "Pending change orders represent unapproved budget adjustments. If approved, project budget increases. If rejected, scope must be reduced.",
            "category": None,
            "amount_at_risk": round(total_pending, 2),
            "items": [{"co_number": co.co_number, "description": co.description, "amount": co.amount} for co in pending_cos[:5]],
        })

    sev_order = {"high": 0, "warning": 1, "info": 2}
    signals.sort(key=lambda s: sev_order.get(s["severity"], 3))

    total_at_risk = sum(s.get("amount_at_risk", 0) for s in signals)

    return {
        "signals": signals,
        "signal_count": len(signals),
        "high_count": sum(1 for s in signals if s["severity"] == "high"),
        "total_at_risk": round(total_at_risk, 2),
        "co_velocity": co_velocity_signal,
        "pending_co_count": len(pending_cos) if 'pending_cos' in dir() else 0,
        "total_change_orders": len(change_orders),
    }


# ─── Feature 13: Vendor Risk Memory ──────────────────────────────────────────

def vendor_risk_memory(all_invoices: List[Any], all_change_orders: List[Any],
                        all_lien_waivers: List[Any]) -> List[dict]:
    """Cross-project vendor risk profiles — learn which vendors cause overruns,
    COs, late waivers, duplicates, or rejection-prone submissions."""
    from collections import defaultdict

    vendor_data: dict = defaultdict(lambda: {
        "invoice_count": 0,
        "total_invoiced": 0.0,
        "total_submitted": 0.0,
        "total_approved": 0.0,
        "total_rejected": 0.0,
        "overdue_count": 0,
        "duplicate_numbers": set(),
        "invoice_numbers": [],
        "co_count": 0,
        "co_total": 0.0,
        "waiver_count": 0,
        "unconditional_waiver_count": 0,
        "rejected_count": 0,
        "partial_approval_count": 0,
    })

    today = _today()

    # Aggregate invoice data per vendor
    for inv in all_invoices:
        vendor = (inv.vendor_name or "Unknown").strip()
        d = vendor_data[vendor]
        d["invoice_count"] += 1
        total = inv.total_due or 0
        d["total_invoiced"] += total
        d["total_submitted"] += inv.lender_submitted_amt or total
        d["total_approved"] += inv.lender_approved_amt or 0
        if inv.lender_status == "rejected":
            d["total_rejected"] += inv.lender_submitted_amt or total
            d["rejected_count"] += 1
        if inv.lender_approved_amt and inv.lender_submitted_amt and inv.lender_approved_amt < inv.lender_submitted_amt * 0.95:
            d["partial_approval_count"] += 1

        # Overdue check
        due = inv.due_date or inv.invoice_date
        if due and inv.payment_status != "paid":
            days = _days_between(due, today) or 0
            if days > 60:
                d["overdue_count"] += 1

        # Duplicate invoice numbers
        inv_num = inv.invoice_number
        if inv_num:
            if inv_num in d["invoice_numbers"]:
                d["duplicate_numbers"].add(inv_num)
            d["invoice_numbers"].append(inv_num)

    # CO data
    for co in all_change_orders:
        vendor = (co.issued_by or "Unknown").strip()
        if vendor and vendor != "Unknown":
            vendor_data[vendor]["co_count"] += 1
            vendor_data[vendor]["co_total"] += co.amount or 0

    # Lien waiver data
    for w in all_lien_waivers:
        vendor = (w.vendor_name or "Unknown").strip()
        vendor_data[vendor]["waiver_count"] += 1
        if w.waiver_type == "unconditional":
            vendor_data[vendor]["unconditional_waiver_count"] += 1

    results = []
    for vendor, d in vendor_data.items():
        if vendor == "Unknown" or d["invoice_count"] == 0:
            continue

        # Compute risk score (0 = very risky, 100 = very reliable)
        score = 100
        risk_flags = []
        positive_flags = []

        # Rejection rate
        rejection_rate = d["rejected_count"] / d["invoice_count"] if d["invoice_count"] > 0 else 0
        if rejection_rate > 0.2:
            score -= 25
            risk_flags.append(f"High rejection rate: {rejection_rate:.0%} of invoices rejected by lender")
        elif rejection_rate > 0:
            score -= 10
            risk_flags.append(f"Some lender rejections: {d['rejected_count']} invoice(s)")

        # Partial approval rate
        partial_rate = d["partial_approval_count"] / d["invoice_count"] if d["invoice_count"] > 0 else 0
        if partial_rate > 0.3:
            score -= 15
            risk_flags.append(f"Frequent partial approvals: {partial_rate:.0%} of invoices partially approved")

        # Overdue payments
        overdue_rate = d["overdue_count"] / d["invoice_count"] if d["invoice_count"] > 0 else 0
        if overdue_rate > 0.3:
            score -= 15
            risk_flags.append(f"{d['overdue_count']} invoice(s) overdue >60 days")
        elif d["overdue_count"] == 0:
            positive_flags.append("No overdue invoices")

        # Duplicate invoices
        if d["duplicate_numbers"]:
            score -= 20
            risk_flags.append(f"Duplicate invoice numbers detected: {', '.join(list(d['duplicate_numbers'])[:3])}")

        # Change orders
        if d["invoice_count"] > 0:
            co_per_inv = d["co_count"] / d["invoice_count"]
            if co_per_inv > 0.5:
                score -= 15
                risk_flags.append(f"High CO rate: {d['co_count']} change orders across {d['invoice_count']} invoices")
            elif d["co_count"] == 0:
                positive_flags.append("No change orders")

        # Lien waiver compliance
        if d["invoice_count"] > 2:
            if d["unconditional_waiver_count"] == 0:
                score -= 15
                risk_flags.append("No unconditional lien waivers on file")
            elif d["waiver_count"] > 0:
                positive_flags.append("Lien waivers on file")

        score = max(0, min(100, score))
        risk_level = "critical" if score < 40 else "high" if score < 60 else "medium" if score < 75 else "low"

        # Approval rate
        approval_rate = round(d["total_approved"] / d["total_submitted"] * 100, 1) if d["total_submitted"] > 0 else None

        results.append({
            "vendor": vendor,
            "invoice_count": d["invoice_count"],
            "total_invoiced": round(d["total_invoiced"], 2),
            "total_submitted": round(d["total_submitted"], 2),
            "total_approved": round(d["total_approved"], 2),
            "approval_rate": approval_rate,
            "rejection_count": d["rejected_count"],
            "partial_approval_count": d["partial_approval_count"],
            "overdue_count": d["overdue_count"],
            "duplicate_count": len(d["duplicate_numbers"]),
            "co_count": d["co_count"],
            "co_total": round(d["co_total"], 2),
            "waiver_count": d["waiver_count"],
            "unconditional_waiver_count": d["unconditional_waiver_count"],
            "risk_score": score,
            "risk_level": risk_level,
            "risk_flags": risk_flags,
            "positive_flags": positive_flags,
        })

    results.sort(key=lambda r: r["risk_score"])
    return results
