"""Client/Homeowner Communication Hub — progress posts, messages, weather, cash flow."""
import os
from datetime import datetime, date, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Optional

from ..database import SessionLocal, get_db
from ..dependencies import get_current_user, require_org_member, get_current_org, FINANCE_READ_ROLES, FINANCE_WRITE_ROLES, call_gemini_api
from ..models import (
    ClientHubPost, ClientMessage, Project, Invoice, Draw,
    UnionAgreement, CloseoutItem, CostCategory, InvoiceAllocation, ChangeOrder
)

router = APIRouter(prefix="/api/project", tags=["client-hub"])
_weather_router = APIRouter(prefix="/api", tags=["weather"])
_union_router = APIRouter(prefix="/api/project", tags=["union"])
_closeout_router = APIRouter(prefix="/api/project", tags=["closeout"])


def get_db_local():
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


# ── Progress Posts ──────────────────────────────────────────────────────────────

@router.get("/{project_id}/hub/posts")
def list_posts(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    posts = db.query(ClientHubPost).filter(ClientHubPost.project_id == project_id).order_by(ClientHubPost.created_at.desc()).all()
    return [{"id": p.id, "title": p.title, "body": p.body, "milestone": p.milestone,
             "visibility": p.visibility, "created_at": p.created_at.isoformat()} for p in posts]


@router.post("/{project_id}/hub/posts")
def create_post(project_id: int, body: dict, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    post = ClientHubPost(
        org_id=p.org_id, project_id=project_id,
        title=body["title"], body=body.get("body"),
        milestone=body.get("milestone"), visibility=body.get("visibility", "client"),
        created_by=user.id,
    )
    db.add(post); db.commit(); db.refresh(post)
    return {"id": post.id, "ok": True}


@router.delete("/{project_id}/hub/posts/{post_id}")
def delete_post(project_id: int, post_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    post = db.query(ClientHubPost).filter(ClientHubPost.id == post_id, ClientHubPost.project_id == project_id).first()
    if post: db.delete(post); db.commit()
    return {"ok": True}


# ── Messages ────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/hub/messages")
def list_messages(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    msgs = db.query(ClientMessage).filter(ClientMessage.project_id == project_id).order_by(ClientMessage.created_at).all()
    return [{"id": m.id, "sender_type": m.sender_type, "sender_name": m.sender_name,
             "message": m.message, "is_read": m.is_read,
             "created_at": m.created_at.isoformat()} for m in msgs]


@router.post("/{project_id}/hub/messages")
def send_message(project_id: int, body: dict, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    m = ClientMessage(
        org_id=p.org_id, project_id=project_id,
        sender_type="gc", sender_name=user.username,
        message=body["message"], is_read=False,
    )
    db.add(m); db.commit()
    return {"ok": True}


@router.put("/{project_id}/hub/messages/{msg_id}/read")
def mark_read(project_id: int, msg_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    m = db.query(ClientMessage).filter(ClientMessage.id == msg_id, ClientMessage.project_id == project_id).first()
    if m: m.is_read = True; db.commit()
    return {"ok": True}


# ── Cash Flow S-Curve ────────────────────────────────────────────────────────────

@router.get("/{project_id}/cash-flow-scurve")
def cash_flow_scurve(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    """Generate cash flow S-curve: planned vs actual cumulative spend by month."""
    proj = _proj(project_id, user, db)

    start = proj.start_date or "2024-01-01"
    end = proj.end_date or (date.today() + timedelta(days=365)).isoformat()
    budget = proj.total_budget or 0

    # Approved COs
    co_total = sum(c.amount for c in db.query(ChangeOrder).filter(
        ChangeOrder.project_id == project_id, ChangeOrder.status == "approved"
    ).all())
    revised_budget = budget + co_total

    # Actual: cumulative invoiced by month
    invoices = db.query(Invoice).filter(
        Invoice.project_id == project_id, Invoice.status == "processed",
        Invoice.invoice_date != None
    ).all()

    monthly_actual = {}
    for inv in invoices:
        try:
            month_key = inv.invoice_date[:7]  # YYYY-MM
            monthly_actual[month_key] = monthly_actual.get(month_key, 0) + (inv.lender_submitted_amt or inv.total_due or 0)
        except Exception:
            pass

    # Build timeline months
    try:
        start_dt = datetime.strptime(start[:7], "%Y-%m")
        end_dt = datetime.strptime(end[:7], "%Y-%m")
    except Exception:
        return {"months": [], "planned": [], "actual": [], "revised_budget": revised_budget}

    months = []
    current = start_dt
    while current <= end_dt:
        months.append(current.strftime("%Y-%m"))
        if current.month == 12:
            current = current.replace(year=current.year+1, month=1)
        else:
            current = current.replace(month=current.month+1)

    n = len(months)
    if n == 0: return {"months": [], "planned": [], "actual": [], "revised_budget": revised_budget}

    # S-curve planned: bell-curve distribution (weighted toward middle)
    import math
    weights = [math.exp(-0.5 * ((i / (n-1) - 0.5) / 0.2) ** 2) if n > 1 else 1 for i in range(n)]
    total_w = sum(weights)
    planned_monthly = [revised_budget * w / total_w for w in weights]
    planned_cum = []
    running = 0
    for v in planned_monthly:
        running += v
        planned_cum.append(round(running, 2))

    # Actual cumulative
    actual_cum = []
    running = 0
    for m in months:
        running += monthly_actual.get(m, 0)
        actual_cum.append(round(running, 2))

    return {
        "months": months, "planned": planned_cum, "actual": actual_cum,
        "revised_budget": revised_budget, "total_invoiced": sum(monthly_actual.values()),
    }


# ── Weather API (Open-Meteo, free, no key) ────────────────────────────────────

@_weather_router.get("/weather")
async def get_weather(lat: float, lon: float, log_date: str):
    """Fetch weather for a location and date from Open-Meteo (free, no API key)."""
    import httpx
    try:
        url = (f"https://api.open-meteo.com/v1/archive"
               f"?latitude={lat}&longitude={lon}"
               f"&start_date={log_date}&end_date={log_date}"
               f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
               f"&timezone=auto")
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(url)
        if resp.status_code != 200:
            # For future dates, use forecast endpoint
            url2 = (f"https://api.open-meteo.com/v1/forecast"
                    f"?latitude={lat}&longitude={lon}"
                    f"&daily=temperature_2m_max,temperature_2m_min,precipitation_sum,windspeed_10m_max"
                    f"&timezone=auto&forecast_days=14")
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.get(url2)
        data = resp.json()
        daily = data.get("daily", {})
        idx = 0
        dates = daily.get("time", [])
        if log_date in dates:
            idx = dates.index(log_date)
        t_max = daily.get("temperature_2m_max", [None])[idx] if daily.get("temperature_2m_max") else None
        t_min = daily.get("temperature_2m_min", [None])[idx] if daily.get("temperature_2m_min") else None
        precip = daily.get("precipitation_sum", [0])[idx] if daily.get("precipitation_sum") else 0
        wind = daily.get("windspeed_10m_max", [0])[idx] if daily.get("windspeed_10m_max") else 0
        condition = "sunny"
        if precip and precip > 10: condition = "rain"
        elif precip and precip > 0: condition = "cloudy"
        if t_max and t_max < 0 and precip: condition = "snow"
        if wind and wind > 40: condition = "wind"
        temp_str = f"{t_min:.0f}°C to {t_max:.0f}°C" if t_max is not None and t_min is not None else ""
        return {
            "condition": condition, "temperature": temp_str,
            "t_max": t_max, "t_min": t_min, "precipitation_mm": precip, "wind_kmh": wind,
        }
    except Exception as e:
        return {"condition": "", "temperature": "", "error": str(e)}


# ── Trade Union Compliance ────────────────────────────────────────────────────

@_union_router.get("/{project_id}/unions")
def list_unions(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    rows = db.query(UnionAgreement).filter(UnionAgreement.project_id == project_id).order_by(UnionAgreement.trade).all()
    result = []
    for r in rows:
        # Apprenticeship ratio compliance check
        ratio_parts = r.apprentice_ratio.split(":") if r.apprentice_ratio else []
        required_journeymen = int(ratio_parts[1]) if len(ratio_parts) == 2 else None
        max_apprentices = (r.journeymen_count // required_journeymen) if (required_journeymen and r.journeymen_count and required_journeymen > 0) else None
        ratio_ok = (r.apprentice_count <= max_apprentices) if max_apprentices is not None else None
        result.append({
            "id": r.id, "trade": r.trade, "local_number": r.local_number,
            "agreement_type": r.agreement_type, "apprentice_ratio": r.apprentice_ratio,
            "journeymen_count": r.journeymen_count, "apprentice_count": r.apprentice_count,
            "max_apprentices_allowed": max_apprentices, "ratio_compliant": ratio_ok,
            "expiry_date": r.expiry_date, "notes": r.notes,
        })
    return result


@_union_router.post("/{project_id}/unions")
def create_union(project_id: int, body: dict, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = UnionAgreement(
        org_id=p.org_id, project_id=project_id,
        trade=body["trade"], local_number=body.get("local_number"),
        agreement_type=body.get("agreement_type", "iba"),
        apprentice_ratio=body.get("apprentice_ratio"),
        journeymen_count=body.get("journeymen_count", 0),
        apprentice_count=body.get("apprentice_count", 0),
        expiry_date=body.get("expiry_date"), notes=body.get("notes"),
        created_by=user.id,
    )
    db.add(r); db.commit(); db.refresh(r)
    return {"id": r.id, "ok": True}


@_union_router.put("/{project_id}/unions/{union_id}")
def update_union(project_id: int, union_id: int, body: dict, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = db.query(UnionAgreement).filter(UnionAgreement.id == union_id, UnionAgreement.project_id == project_id).first()
    if not r: raise HTTPException(404)
    for f in ["trade","local_number","agreement_type","apprentice_ratio","journeymen_count","apprentice_count","expiry_date","notes"]:
        if f in body: setattr(r, f, body[f])
    db.commit()
    return {"ok": True}


@_union_router.delete("/{project_id}/unions/{union_id}")
def delete_union(project_id: int, union_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    r = db.query(UnionAgreement).filter(UnionAgreement.id == union_id, UnionAgreement.project_id == project_id).first()
    if r: db.delete(r); db.commit()
    return {"ok": True}


# ── Project Closeout ────────────────────────────────────────────────────────────

CLOSEOUT_DEFAULTS = [
    ("documents", "As-built drawings received from all trades"),
    ("documents", "Operation & Maintenance manuals submitted"),
    ("documents", "Attic stock / spare materials delivered"),
    ("warranties", "Equipment warranties registered with manufacturers"),
    ("warranties", "Subcontractor warranty letters received"),
    ("warranties", "TARION enrollment confirmation"),
    ("inspections", "Occupancy permit obtained"),
    ("inspections", "Fire marshal inspection passed"),
    ("inspections", "Final building inspection completed"),
    ("financial", "Final lender draw submitted and approved"),
    ("financial", "All holdback released or lien period cleared"),
    ("financial", "All subcontractors paid — final lien waivers received"),
    ("financial", "Statutory declarations received from all trades"),
    ("financial", "T5018 reporting completed for contractors paid >$500"),
    ("legal", "Substantial performance declared and published"),
    ("legal", "Certificate of Substantial Performance filed"),
    ("legal", "All change orders signed and closed"),
    ("training", "Owner/operator training completed"),
    ("training", "Building systems commissioning records delivered"),
]


@_closeout_router.get("/{project_id}/closeout")
def list_closeout(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    items = db.query(CloseoutItem).filter(CloseoutItem.project_id == project_id).order_by(CloseoutItem.category, CloseoutItem.id).all()
    return [{"id": i.id, "category": i.category, "item_name": i.item_name,
             "description": i.description, "responsible_party": i.responsible_party,
             "due_date": i.due_date, "status": i.status, "notes": i.notes,
             "completed_at": i.completed_at.isoformat() if i.completed_at else None} for i in items]


@_closeout_router.post("/{project_id}/closeout/seed")
def seed_closeout(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    """Seed the standard closeout checklist for this project."""
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    existing = db.query(CloseoutItem).filter(CloseoutItem.project_id == project_id).count()
    if existing: return {"ok": True, "message": "Checklist already exists"}
    for cat, name in CLOSEOUT_DEFAULTS:
        db.add(CloseoutItem(org_id=p.org_id, project_id=project_id, category=cat, item_name=name, created_by=user.id))
    db.commit()
    return {"ok": True, "seeded": len(CLOSEOUT_DEFAULTS)}


@_closeout_router.post("/{project_id}/closeout")
def create_closeout_item(project_id: int, body: dict, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    i = CloseoutItem(
        org_id=p.org_id, project_id=project_id,
        category=body.get("category", "documents"),
        item_name=body["item_name"], description=body.get("description"),
        responsible_party=body.get("responsible_party"), due_date=body.get("due_date"),
        status=body.get("status", "pending"), notes=body.get("notes"), created_by=user.id,
    )
    db.add(i); db.commit(); db.refresh(i)
    return {"id": i.id, "ok": True}


@_closeout_router.put("/{project_id}/closeout/{item_id}")
def update_closeout(project_id: int, item_id: int, body: dict, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    i = db.query(CloseoutItem).filter(CloseoutItem.id == item_id, CloseoutItem.project_id == project_id).first()
    if not i: raise HTTPException(404)
    for f in ["category","item_name","description","responsible_party","due_date","status","notes"]:
        if f in body: setattr(i, f, body[f])
    if body.get("status") == "complete" and not i.completed_at:
        i.completed_at = datetime.utcnow()
    elif body.get("status") != "complete":
        i.completed_at = None
    db.commit()
    return {"ok": True}


@_closeout_router.delete("/{project_id}/closeout/{item_id}")
def delete_closeout(project_id: int, item_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    i = db.query(CloseoutItem).filter(CloseoutItem.id == item_id, CloseoutItem.project_id == project_id).first()
    if i: db.delete(i); db.commit()
    return {"ok": True}


@_closeout_router.get("/{project_id}/closeout/summary")
def closeout_summary(project_id: int, db: Session = Depends(get_db_local), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    items = db.query(CloseoutItem).filter(CloseoutItem.project_id == project_id).all()
    total = len(items)
    complete = sum(1 for i in items if i.status == "complete")
    pct = round(complete / total * 100) if total else 0
    by_cat = {}
    for i in items:
        if i.category not in by_cat:
            by_cat[i.category] = {"total": 0, "complete": 0}
        by_cat[i.category]["total"] += 1
        if i.status == "complete":
            by_cat[i.category]["complete"] += 1
    return {"total": total, "complete": complete, "pct_complete": pct, "by_category": by_cat}


# ── AI Weekly Client Update Generator ──────────────────────────────────────────

@router.post("/{project_id}/ai-client-update")
async def generate_ai_client_update(project_id: int, body: dict = None,
                                     db: Session = Depends(get_db_local),
                                     user=Depends(get_current_user)):
    """
    Gemini summarizes the past 7 days of daily logs, RFIs, milestones, and photos
    into a clean, professional weekly client update email.
    """
    p = _proj(project_id, user, db)

    from sqlalchemy import text
    week_ago = (date.today() - timedelta(days=7)).strftime("%Y-%m-%d")
    tone = (body or {}).get("tone", "professional")  # professional | friendly | formal

    # Gather last 7 days of daily logs
    logs = db.execute(text("""
        SELECT log_date, weather, crew_count, work_summary, issues, delays
        FROM pm_daily_logs
        WHERE project_id=:pid AND log_date >= :wa
        ORDER BY log_date DESC LIMIT 10
    """), {"pid": project_id, "wa": week_ago}).fetchall()

    # Open RFIs this week
    rfis = db.execute(text("""
        SELECT rfi_number, subject, status FROM pm_rfis
        WHERE project_id=:pid AND created_at >= :wa ORDER BY created_at DESC LIMIT 15
    """), {"pid": project_id, "wa": week_ago}).fetchall()

    # Milestones nearing or just hit
    milestones = db.execute(text("""
        SELECT name, status, pct_complete, target_date FROM milestones
        WHERE project_id=:pid ORDER BY target_date ASC LIMIT 10
    """), {"pid": project_id}).fetchall()

    # Change orders this week
    cos = db.execute(text("""
        SELECT co_number, description, amount, status FROM change_orders
        WHERE project_id=:pid AND date >= :wa ORDER BY date DESC LIMIT 10
    """), {"pid": project_id, "wa": week_ago}).fetchall()

    # Build context string
    ctx_parts = [f"Project: {p.name}"]
    if logs:
        ctx_parts.append("DAILY LOGS THIS WEEK:")
        for l in logs:
            ctx_parts.append(f"  {l[0]}: Crew {l[2]}, Weather {l[1]}\n  Work: {l[3] or 'N/A'}\n  Issues: {l[4] or 'None'}\n  Delays: {l[5] or 'None'}")
    if milestones:
        ctx_parts.append("MILESTONES:")
        for m in milestones:
            ctx_parts.append(f"  {m[0]}: {m[1]} ({m[2]}% complete, target {m[3]})")
    if rfis:
        ctx_parts.append("RFIs THIS WEEK:")
        for r in rfis:
            ctx_parts.append(f"  RFI {r[0]}: {r[1]} [{r[2]}]")
    if cos:
        ctx_parts.append("CHANGE ORDERS THIS WEEK:")
        for c in cos:
            ctx_parts.append(f"  CO {c[0]}: {c[1]} — ${c[2]:,.2f} [{c[3]}]")

    context = "\n".join(ctx_parts)

    prompt = f"""You are writing a weekly construction progress update for a homeowner or building owner.
The tone should be {tone}. Write a professional email update (300-450 words) covering:
1. Overall progress summary
2. Key work completed this week
3. Upcoming work next week (infer from context)
4. Any issues or delays (explain in plain language, not construction jargon)
5. A positive, reassuring closing

Use plain language — the client is not a construction professional.
Do not include any dollar amounts from change orders unless they are approved.
Start with "Subject: Weekly Construction Update — [Project name] — Week of [date]"

PROJECT DATA:
{context}"""

    result = await call_gemini_api(
        {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.7, "maxOutputTokens": 1024},
        },
        timeout=45,
    )
    update_text = result["candidates"][0]["content"]["parts"][0]["text"]

    return {
        "update": update_text,
        "week_of": week_ago,
        "project_name": p.name,
        "logs_included": len(logs),
        "milestones_included": len(milestones),
    }
