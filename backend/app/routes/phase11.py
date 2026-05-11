"""
Phase 11 — Final Platform Completions
- QB Desktop IIF export (QuickBooks Desktop TRNS/SPL format)
- Sage 50 Canada CSV import format export
- Manual bank statement importer (RBC, TD, Scotiabank, BMO CSV detection + AP matching)
- AI Change Order narrative generator (Gemini drafts professional CO justification letters)
- Multi-currency FX tracking on invoices
- Stress testing / scenario modeling (interest reserve burn, rate sensitivity)
"""
from __future__ import annotations

import io
import csv
import json
import os
from datetime import datetime, timedelta, date
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, JSONResponse
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, require_project_access
from ..models import User

router = APIRouter(prefix="/api", tags=["phase11"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── QB Desktop IIF Export ────────────────────────────────────────────────────

@router.get("/reports/export/qb-iif/{project_id}")
def export_qb_iif(project_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """
    Export invoices as QuickBooks Desktop IIF (Intuit Interchange Format).
    Imports directly via QB Desktop → File → Utilities → Import → IIF Files.
    """
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    invoices = db.execute(text("""
        SELECT i.invoice_number, i.vendor_name, i.invoice_date, i.total,
               i.subtotal, i.tax_gst, i.tax_hst, i.tax_pst, i.tax_qst,
               i.payment_status, i.notes,
               cc.name as category_name
        FROM invoices i
        LEFT JOIN cost_categories cc ON i.category_id = cc.id
        WHERE i.project_id = :pid AND i.org_id = :oid
        ORDER BY i.invoice_date
    """), {"pid": project_id, "oid": current_user.org_id}).fetchall()

    lines = []
    # IIF Header blocks
    lines.append("!TRNS\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\tCLEAR\tTOPRINT")
    lines.append("!SPL\tTRNSTYPE\tDATE\tACCNT\tNAME\tAMOUNT\tDOCNUM\tMEMO\tQNTY\tINVITEM\tTAXABLE")
    lines.append("!ENDTRNS")

    for inv in invoices:
        inv_num = inv[0] or "NOINV"
        vendor = (inv[1] or "Unknown Vendor").replace("\t", " ")
        inv_date_raw = inv[2] or datetime.now().strftime("%Y-%m-%d")
        try:
            dt = datetime.strptime(str(inv_date_raw)[:10], "%Y-%m-%d")
            qb_date = dt.strftime("%m/%d/%Y")
        except Exception:
            qb_date = datetime.now().strftime("%m/%d/%Y")
        total = float(inv[3] or 0)
        subtotal = float(inv[4] or total)
        gst = float(inv[5] or 0)
        hst = float(inv[6] or 0)
        pst = float(inv[7] or 0)
        qst = float(inv[8] or 0)
        cat = (inv[11] or "Construction Costs").replace("\t", " ")
        memo = (inv[10] or "").replace("\t", " ")[:50]

        # TRNS line (AP credit)
        lines.append(f"TRNS\tBILL\t{qb_date}\tAccounts Payable\t{vendor}\t{-total:.2f}\t{inv_num}\t{memo}\tN\tN")
        # SPL line for expense
        lines.append(f"SPL\tBILL\t{qb_date}\t{cat}\t{vendor}\t{subtotal:.2f}\t{inv_num}\t{memo}\t1\t\tN")
        # SPL lines for taxes
        if gst > 0:
            lines.append(f"SPL\tBILL\t{qb_date}\tGST Paid\t{vendor}\t{gst:.2f}\t{inv_num}\tGST\t\t\tN")
        if hst > 0:
            lines.append(f"SPL\tBILL\t{qb_date}\tHST Paid\t{vendor}\t{hst:.2f}\t{inv_num}\tHST\t\t\tN")
        if pst > 0:
            lines.append(f"SPL\tBILL\t{qb_date}\tPST Paid\t{vendor}\t{pst:.2f}\t{inv_num}\tPST\t\t\tN")
        if qst > 0:
            lines.append(f"SPL\tBILL\t{qb_date}\tQST Paid\t{vendor}\t{qst:.2f}\t{inv_num}\tQST\t\t\tN")
        lines.append("ENDTRNS")

    content = "\r\n".join(lines) + "\r\n"
    filename = f"Finel_QB_IIF_Project{project_id}_{date.today()}.iif"
    return StreamingResponse(
        io.BytesIO(content.encode("ascii", errors="replace")),
        media_type="text/plain",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ─── Sage 50 Canada CSV Export ────────────────────────────────────────────────

@router.get("/reports/export/sage50/{project_id}")
def export_sage50(project_id: int, db: Session = Depends(get_db),
                  current_user: User = Depends(get_current_user)):
    """
    Export invoices in Sage 50 Canada Purchase Journal import CSV format.
    Import via Sage 50 → File → Import/Export → Import Transactions.
    """
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    invoices = db.execute(text("""
        SELECT i.invoice_number, i.vendor_name, i.invoice_date, i.total,
               i.subtotal, i.tax_gst, i.tax_hst, i.tax_pst, i.tax_qst,
               i.payment_status, i.notes, i.due_date,
               cc.name as category_name
        FROM invoices i
        LEFT JOIN cost_categories cc ON i.category_id = cc.id
        WHERE i.project_id = :pid AND i.org_id = :oid
        ORDER BY i.invoice_date
    """), {"pid": project_id, "oid": current_user.org_id}).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)

    # Sage 50 CA Purchase Journal import headers
    writer.writerow([
        "Transaction Type", "Date", "Supplier Name", "Invoice/Reference",
        "Description", "Account Number", "Account Description",
        "Amount Before Tax", "Tax Amount", "Tax Code", "Total",
        "Due Date", "Payment Status", "Internal Reference"
    ])

    for inv in invoices:
        inv_num = inv[0] or ""
        vendor = inv[1] or "Unknown Vendor"
        inv_date_raw = str(inv[2] or "")[:10]
        subtotal = float(inv[4] or inv[3] or 0)
        gst = float(inv[5] or 0)
        hst = float(inv[6] or 0)
        pst = float(inv[7] or 0)
        qst = float(inv[8] or 0)
        tax_total = gst + hst + pst + qst
        total = float(inv[3] or 0)
        # Tax code: H (HST), G (GST), G+P (GST+PST), Q (QST+GST)
        if hst > 0:
            tax_code = "H"
        elif qst > 0:
            tax_code = "G+Q"
        elif pst > 0:
            tax_code = "G+P"
        elif gst > 0:
            tax_code = "G"
        else:
            tax_code = ""
        cat = inv[12] or "5000"
        due_date = str(inv[11] or "")[:10]
        notes = (inv[10] or "").replace("\n", " ")[:100]

        writer.writerow([
            "Purchase", inv_date_raw, vendor, inv_num,
            notes, "5000", cat,
            f"{subtotal:.2f}", f"{tax_total:.2f}", tax_code, f"{total:.2f}",
            due_date, inv[9] or "unpaid", inv_num
        ])

    content = output.getvalue().encode("utf-8-sig")  # BOM for Excel/Sage compatibility
    filename = f"Finel_Sage50_Project{project_id}_{date.today()}.csv"
    return StreamingResponse(
        io.BytesIO(content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


# ─── Bank Statement Importer ──────────────────────────────────────────────────

def _detect_bank_format(headers: list[str]) -> str:
    """Auto-detect bank CSV format from column headers."""
    h = [x.lower().strip().replace('"', '') for x in headers]
    joined = ",".join(h)
    if "account number" in joined and "cheque number" in joined:
        return "rbc"
    if "transaction date" in joined and "debit amount" in joined and "credit amount" in joined:
        return "td"
    if "date" in joined and "withdrawals" in joined and "deposits" in joined:
        return "scotiabank"
    if "transaction date" in joined and "description" in joined and "debit" in joined:
        return "bmo"
    if "date" in joined and "amount" in joined:
        return "generic"
    return "unknown"


def _parse_bank_csv(content: str) -> tuple[str, list[dict]]:
    """Parse bank CSV content, auto-detect format, return (bank_name, transactions)."""
    lines = content.strip().splitlines()
    # Skip non-CSV header lines (RBC has account info rows before headers)
    for i, line in enumerate(lines):
        if "," in line and len(line.split(",")) >= 4:
            header_line = i
            break
    else:
        raise ValueError("Could not find CSV headers")

    reader = csv.DictReader(lines[header_line:])
    rows = list(reader)
    if not rows:
        raise ValueError("No transactions found")

    bank = _detect_bank_format(list(rows[0].keys()))
    transactions = []

    for row in rows:
        row_lower = {k.lower().strip(): v.strip() for k, v in row.items() if k}
        txn = {}

        if bank == "rbc":
            txn["date"] = row_lower.get("transaction date", "")
            txn["description"] = row_lower.get("description 1", "") + " " + row_lower.get("description 2", "")
            debit = row_lower.get("cad$", "0").replace("$", "").replace(",", "") or "0"
            txn["amount"] = -abs(float(debit)) if float(debit) != 0 else 0
        elif bank == "td":
            txn["date"] = row_lower.get("transaction date", "")
            txn["description"] = row_lower.get("description", "")
            debit = row_lower.get("debit amount", "0").replace(",", "") or "0"
            credit = row_lower.get("credit amount", "0").replace(",", "") or "0"
            txn["amount"] = float(credit) - float(debit)
        elif bank == "scotiabank":
            txn["date"] = row_lower.get("date", "")
            txn["description"] = row_lower.get("description", "")
            wd = row_lower.get("withdrawals", "0").replace(",", "") or "0"
            dep = row_lower.get("deposits", "0").replace(",", "") or "0"
            txn["amount"] = float(dep) - float(wd)
        elif bank == "bmo":
            txn["date"] = row_lower.get("transaction date", "")
            txn["description"] = row_lower.get("description", "")
            debit = row_lower.get("debit", "0").replace(",", "") or "0"
            credit = row_lower.get("credit", "0").replace(",", "") or "0"
            txn["amount"] = float(credit) - float(debit)
        else:
            txn["date"] = row_lower.get("date", "")
            txn["description"] = row_lower.get("description", row_lower.get("memo", ""))
            amount_str = row_lower.get("amount", "0").replace(",", "").replace("$", "") or "0"
            txn["amount"] = float(amount_str)

        txn["description"] = txn["description"].strip()
        txn["raw"] = dict(row)
        if txn["date"] and txn["description"]:
            transactions.append(txn)

    return bank, transactions


@router.post("/bank-import/parse")
async def parse_bank_statement(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Upload a bank CSV statement; detect format, parse transactions, return for review."""
    require_org_member(db, current_user.org_id, current_user.id)
    content_bytes = await file.read()
    try:
        content = content_bytes.decode("utf-8-sig", errors="replace")
        bank, transactions = _parse_bank_csv(content)
    except Exception as e:
        raise HTTPException(400, f"Could not parse bank statement: {e}")

    return {
        "bank_detected": bank,
        "transaction_count": len(transactions),
        "transactions": transactions[:500],  # max 500 rows
    }


@router.post("/bank-import/match")
async def match_bank_to_invoices(body: dict,
                                  db: Session = Depends(get_db),
                                  current_user: User = Depends(get_current_user)):
    """
    Match parsed bank transactions to unpaid AP invoices by amount and fuzzy vendor name.
    Returns suggested matches for user review.
    """
    require_org_member(db, current_user.org_id, current_user.id)
    transactions = body.get("transactions", [])
    project_id = body.get("project_id")

    # Load unpaid invoices
    q = """
        SELECT id, invoice_number, vendor_name, total, invoice_date
        FROM invoices
        WHERE org_id=:oid AND payment_status='unpaid'
    """
    params = {"oid": current_user.org_id}
    if project_id:
        q += " AND project_id=:pid"
        params["pid"] = project_id
    invoices = db.execute(text(q), params).fetchall()

    matches = []
    for txn in transactions:
        txn_amount = abs(float(txn.get("amount", 0)))
        if txn_amount == 0:
            continue
        txn_desc = (txn.get("description", "") or "").lower()
        best_match = None
        best_score = 0

        for inv in invoices:
            inv_total = float(inv[2] if len(inv) > 2 else 0)  # Fix: total is index 3
            inv_total = float(inv[3] or 0)
            inv_vendor = (inv[2] or "").lower()
            inv_num = (inv[1] or "").lower()

            # Exact amount match
            amount_match = abs(txn_amount - inv_total) < 0.02
            if not amount_match:
                continue

            # Fuzzy vendor name match
            vendor_words = inv_vendor.split()
            score = sum(1 for w in vendor_words if w in txn_desc and len(w) > 3)
            # Invoice number match
            if inv_num in txn_desc:
                score += 5

            if score > best_score:
                best_score = score
                best_match = {"invoice_id": inv[0], "invoice_number": inv[1], "vendor_name": inv[2], "total": inv_total, "match_score": score}

        matches.append({
            "transaction": txn,
            "suggested_match": best_match,
            "confidence": "high" if best_score >= 3 else "medium" if best_score >= 1 else "none",
        })

    return {"matches": matches, "total": len(matches), "auto_matched": sum(1 for m in matches if m["confidence"] == "high")}


# ─── AI Change Order Narrative Generator ─────────────────────────────────────

@router.post("/project/{project_id}/change-orders/{co_id}/ai-narrative")
async def ai_co_narrative(project_id: int, co_id: int, body: dict,
                          db: Session = Depends(get_db),
                          current_user: User = Depends(get_current_user)):
    """
    Gemini drafts a professional change order justification / claim narrative.
    Input: delay_event, impact_description, time_days, cost_amount.
    Output: formal CO letter suitable for owner/lender submission.
    """
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    api_key = os.getenv("GEMINI_API_KEY", "")
    if not api_key:
        raise HTTPException(503, "GEMINI_API_KEY not configured")

    co = db.execute(text("SELECT co_number, description, amount, status, date FROM change_orders WHERE id=:id AND project_id=:pid"), {"id": co_id, "pid": project_id}).fetchone()
    project = db.execute(text("SELECT name, province FROM projects WHERE id=:id"), {"id": project_id}).fetchone()
    if not co:
        raise HTTPException(404, "Change order not found")

    delay_event = body.get("delay_event", co[1] or "Owner-directed change")
    impact_description = body.get("impact_description", "")
    time_days = body.get("time_days", 0)
    cost_amount = body.get("cost_amount", float(co[2] or 0))
    contract_type = body.get("contract_type", "CCDC 2")
    province = (project[1] if project else None) or "ON"

    prompt = f"""You are a senior Canadian construction claims consultant writing a formal change order justification letter.

Write a professional, legally precise change order narrative for submission to the project owner and lender.
This must be suitable for a {contract_type} contract in {province}, Canada.

CHANGE ORDER DETAILS:
- CO Number: {co[0]}
- Project: {project[0] if project else 'Construction Project'}
- Event: {delay_event}
- Impact: {impact_description or 'Scope change requiring additional work and resources'}
- Time Impact: {time_days} calendar days
- Cost Impact: ${cost_amount:,.2f} CAD
- Event Date: {co[4] or datetime.now().strftime('%Y-%m-%d')}

Write the narrative in this structure:
1. BACKGROUND — what the original contract scope was
2. CHANGE EVENT — what happened and when (owner directive, unforeseen condition, design change, etc.)
3. ENTITLEMENT — why the Contractor is entitled to additional time and cost under {contract_type} (cite specific GC clauses e.g. GC 6.1, GC 6.2, GC 8.1)
4. TIME IMPACT ANALYSIS — how the {time_days} days is calculated
5. COST IMPACT ANALYSIS — breakdown of the ${cost_amount:,.2f} (labour, material, equipment, overhead at standard markup rates)
6. CONCLUSION — formal request for approval

Tone: Professional, factual, formal. No bullet points — use paragraph form with numbered sections."""

    import httpx
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
            json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.4, "maxOutputTokens": 2048}
            }
        )
    resp.raise_for_status()
    narrative = resp.json()["candidates"][0]["content"]["parts"][0]["text"]
    return {
        "narrative": narrative,
        "co_number": co[0],
        "cost_amount": cost_amount,
        "time_days": time_days,
        "province": province,
    }


# ─── Multi-Currency FX Support ────────────────────────────────────────────────

# Live FX rates sourced from exchangerate-api.com (free tier, no key needed)
_FX_CACHE = {}
_FX_CACHE_TIME = {}
_FX_CACHE_TTL = 3600  # 1 hour

async def _get_fx_rate(from_currency: str, to_currency: str = "CAD") -> float:
    """Fetch FX rate from open.er-api.com (free, no key)."""
    import httpx, time
    cache_key = f"{from_currency}:{to_currency}"
    now = time.time()
    if cache_key in _FX_CACHE and now - _FX_CACHE_TIME.get(cache_key, 0) < _FX_CACHE_TTL:
        return _FX_CACHE[cache_key]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"https://open.er-api.com/v6/latest/{from_currency}")
        if resp.status_code == 200:
            data = resp.json()
            rate = data["rates"].get(to_currency, 1.0)
            _FX_CACHE[cache_key] = rate
            _FX_CACHE_TIME[cache_key] = now
            return rate
    except Exception:
        pass
    # Fallback rates (approximate May 2026)
    fallback = {"USD": 1.36, "EUR": 1.47, "GBP": 1.72, "CAD": 1.0}
    return fallback.get(from_currency, 1.0) if to_currency == "CAD" else 1.0


@router.get("/fx/rates")
async def get_fx_rates():
    """Return live FX rates for common currencies to CAD."""
    rates = {}
    for currency in ["USD", "EUR", "GBP", "AUD", "CHF"]:
        rates[currency] = await _get_fx_rate(currency, "CAD")
    rates["CAD"] = 1.0
    return {"base": "CAD", "rates": rates, "source": "open.er-api.com"}


@router.post("/fx/convert")
async def convert_currency(body: dict):
    """Convert amount from one currency to CAD."""
    amount = float(body.get("amount", 0))
    from_currency = body.get("from_currency", "USD").upper()
    if from_currency == "CAD":
        return {"cad_amount": amount, "rate": 1.0, "from_currency": "CAD"}
    rate = await _get_fx_rate(from_currency, "CAD")
    return {"cad_amount": round(amount * rate, 2), "rate": rate, "from_currency": from_currency}


# ─── Stress Testing / Scenario Modeling ──────────────────────────────────────

@router.post("/project/{project_id}/stress-test")
def run_stress_test(project_id: int, body: dict,
                    db: Session = Depends(get_db),
                    current_user: User = Depends(get_current_user)):
    """
    Run interest reserve burn scenarios and rate sensitivity analysis.
    Scenarios: base case, rate +100bps, rate +200bps, schedule +3mo, schedule +6mo.
    """
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)

    # Get interest reserve data
    reserve_row = db.execute(text("""
        SELECT reserve_amount, drawn_to_date, interest_rate, accrual_basis
        FROM interest_reserves WHERE project_id=:pid AND org_id=:oid
        LIMIT 1
    """), {"pid": project_id, "oid": current_user.org_id}).fetchone()

    # Override with body params or use DB values
    reserve_amount = float(body.get("reserve_amount") or (reserve_row[0] if reserve_row else 0))
    drawn_to_date = float(body.get("drawn_to_date") or (reserve_row[1] if reserve_row else 0))
    base_rate = float(body.get("interest_rate") or (reserve_row[2] if reserve_row else 5.0))
    loan_balance = float(body.get("loan_balance", 0))
    months_remaining = int(body.get("months_remaining", 12))
    pre_sales_threshold = float(body.get("pre_sales_threshold_pct", 70.0))  # % presales required
    current_pre_sales_pct = float(body.get("current_pre_sales_pct", 0.0))

    reserve_remaining = reserve_amount - drawn_to_date

    def _calc_interest_burn(rate_pct: float, months: int, balance: float) -> dict:
        """Calculate monthly interest accrual and reserve exhaustion."""
        monthly_rate = rate_pct / 100 / 12
        monthly_interest = balance * monthly_rate
        total_interest = monthly_interest * months
        exhausted = total_interest > reserve_remaining
        months_to_exhaustion = (reserve_remaining / monthly_interest) if monthly_interest > 0 else float('inf')
        return {
            "monthly_interest": round(monthly_interest, 2),
            "total_projected": round(total_interest, 2),
            "reserve_remaining": round(reserve_remaining, 2),
            "surplus_deficit": round(reserve_remaining - total_interest, 2),
            "exhausted": exhausted,
            "months_to_exhaustion": round(months_to_exhaustion, 1) if months_to_exhaustion != float('inf') else None,
        }

    scenarios = {
        "base_case": _calc_interest_burn(base_rate, months_remaining, loan_balance),
        "rate_plus_100bps": _calc_interest_burn(base_rate + 1.0, months_remaining, loan_balance),
        "rate_plus_200bps": _calc_interest_burn(base_rate + 2.0, months_remaining, loan_balance),
        "schedule_plus_3mo": _calc_interest_burn(base_rate, months_remaining + 3, loan_balance),
        "schedule_plus_6mo": _calc_interest_burn(base_rate, months_remaining + 6, loan_balance),
        "combined_worst": _calc_interest_burn(base_rate + 2.0, months_remaining + 6, loan_balance),
    }

    # Pre-sales / pre-leasing risk
    pre_sales_risk = {
        "required_pct": pre_sales_threshold,
        "current_pct": current_pre_sales_pct,
        "gap_pct": max(0, pre_sales_threshold - current_pre_sales_pct),
        "status": "met" if current_pre_sales_pct >= pre_sales_threshold else "at_risk" if current_pre_sales_pct >= pre_sales_threshold * 0.8 else "breach",
    }

    # LTC/LTV ratios
    project_row = db.execute(text(
        "SELECT total_budget, lender_budget FROM projects WHERE id=:pid"
    ), {"pid": project_id}).fetchone()
    total_budget = float(project_row[0] or 0) if project_row else 0
    ltc = round(loan_balance / total_budget * 100, 1) if total_budget > 0 else None

    return {
        "project_id": project_id,
        "assumptions": {
            "reserve_amount": reserve_amount,
            "drawn_to_date": drawn_to_date,
            "reserve_remaining": reserve_remaining,
            "base_rate_pct": base_rate,
            "loan_balance": loan_balance,
            "months_remaining": months_remaining,
        },
        "interest_reserve_scenarios": scenarios,
        "pre_sales_risk": pre_sales_risk,
        "ltc_ratio_pct": ltc,
        "rag": "red" if scenarios["base_case"]["exhausted"] else "amber" if scenarios["rate_plus_100bps"]["exhausted"] else "green",
        "summary": f"Base case: reserve {'exhausted in ' + str(scenarios['base_case']['months_to_exhaustion']) + ' months' if scenarios['base_case']['exhausted'] else 'sufficient'}. Rate +200bps + 6mo extension: {'BREACH' if scenarios['combined_worst']['exhausted'] else 'OK'}.",
    }


@router.get("/portfolio/stress-dashboard")
def portfolio_stress_dashboard(db: Session = Depends(get_db),
                                current_user: User = Depends(get_current_user)):
    """Cross-portfolio interest reserve stress summary."""
    require_org_member(db, current_user.org_id, current_user.id)
    reserves = db.execute(text("""
        SELECT ir.project_id, p.name, ir.reserve_amount, ir.drawn_to_date, ir.interest_rate
        FROM interest_reserves ir
        JOIN projects p ON ir.project_id = p.id
        WHERE ir.org_id = :oid
    """), {"oid": current_user.org_id}).fetchall()

    results = []
    for r in reserves:
        remaining = float(r[2] or 0) - float(r[3] or 0)
        rate = float(r[4] or 5.0)
        results.append({
            "project_id": r[0], "project_name": r[1],
            "reserve_remaining": remaining,
            "interest_rate": rate,
            "rag": "red" if remaining < 0 else "amber" if remaining < remaining * 0.15 else "green",
        })
    return {"projects": results, "total_reserve_remaining": sum(r["reserve_remaining"] for r in results)}
