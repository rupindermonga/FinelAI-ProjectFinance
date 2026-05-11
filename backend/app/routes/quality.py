"""Quality Inspections, Visitor Log, Estimating Lite."""
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, FINANCE_READ_ROLES, FINANCE_WRITE_ROLES
from ..models import QualityInspection, QualityInspectionItem, VisitorLog, Estimate, EstimateLineItem, Project, CostCategory

router = APIRouter(prefix="/api/project", tags=["quality"])


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


# ── Quality Inspections ─────────────────────────────────────────────────────────

INSPECTION_TEMPLATES = {
    "rough_framing": ["Framing members correctly sized per engineering","Stud spacing meets code","Headers properly supported","Fire blocking installed","Anchor bolts/straps installed","Moisture barrier in place","Rough openings correct size"],
    "concrete": ["Rebar placement per drawings","Cover depth correct","Formwork tight","Vibration during pour","Slump tested","Test cylinders taken","Curing method in place"],
    "electrical": ["Panel location correct","Wire gauge correct","AFCI/GFCI protection","Ground fault protection in wet areas","Junction boxes covered","Conduit properly supported","Smoke detector locations"],
    "plumbing": ["Pipe slopes correct","Cleanouts accessible","Pressure tested","Traps installed","Venting complete","Backflow preventers","Water hammer arrestors"],
    "final": ["All punch items resolved","Occupancy permit received","As-builts submitted","O&M manuals delivered","Training completed","Keys/access fobs provided","Final inspection signed off"],
}

STANDARD_ITEMS = ["Meeting specification requirements","Correct materials/products installed","Quality of workmanship acceptable","No visible deficiencies","Previous deficiencies corrected","Work ready for next phase"]


@router.get("/{project_id}/quality-inspections")
def list_inspections(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    rows = db.query(QualityInspection).filter(QualityInspection.project_id == project_id).order_by(QualityInspection.inspection_date.desc()).all()
    return [{"id": r.id, "inspection_date": r.inspection_date, "inspector_name": r.inspector_name,
             "area_location": r.area_location, "inspection_type": r.inspection_type,
             "status": r.status, "pass_count": r.pass_count, "fail_count": r.fail_count,
             "notes": r.notes, "item_count": len(r.items),
             "created_at": r.created_at.isoformat()} for r in rows]


@router.post("/{project_id}/quality-inspections")
def create_inspection(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    insp = QualityInspection(
        org_id=p.org_id, project_id=project_id,
        inspection_date=body["inspection_date"],
        inspector_name=body.get("inspector_name"),
        area_location=body.get("area_location"),
        inspection_type=body.get("inspection_type", "general"),
        status=body.get("status", "scheduled"),
        notes=body.get("notes"), created_by=user.id,
    )
    db.add(insp); db.commit(); db.refresh(insp)
    # Auto-seed checklist items from template
    insp_type = body.get("inspection_type", "")
    template_items = INSPECTION_TEMPLATES.get(insp_type, STANDARD_ITEMS)
    for i, desc in enumerate(template_items):
        db.add(QualityInspectionItem(inspection_id=insp.id, item_description=desc, result="pending", display_order=i))
    db.commit()
    return {"id": insp.id, "item_count": len(template_items), "ok": True}


@router.get("/{project_id}/quality-inspections/{insp_id}/items")
def get_inspection_items(project_id: int, insp_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    insp = db.query(QualityInspection).filter(QualityInspection.id == insp_id, QualityInspection.project_id == project_id).first()
    if not insp: raise HTTPException(404)
    return {"inspection": {"id": insp.id, "inspection_date": insp.inspection_date, "inspector_name": insp.inspector_name,
                           "area_location": insp.area_location, "inspection_type": insp.inspection_type, "status": insp.status, "notes": insp.notes},
            "items": [{"id": i.id, "item_description": i.item_description, "result": i.result, "notes": i.notes, "display_order": i.display_order} for i in sorted(insp.items, key=lambda x: x.display_order)]}


@router.put("/{project_id}/quality-inspections/{insp_id}/items/{item_id}")
def update_item(project_id: int, insp_id: int, item_id: int, body: dict,
                db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    item = db.query(QualityInspectionItem).filter(QualityInspectionItem.id == item_id, QualityInspectionItem.inspection_id == insp_id).first()
    if not item: raise HTTPException(404)
    for f in ["result","notes"]:
        if f in body: setattr(item, f, body[f])
    # Update parent counts
    insp = db.query(QualityInspection).filter(QualityInspection.id == insp_id).first()
    if insp:
        insp.pass_count = sum(1 for i in insp.items if i.result == "pass")
        insp.fail_count = sum(1 for i in insp.items if i.result == "fail")
        all_done = all(i.result != "pending" for i in insp.items)
        if all_done:
            insp.status = "failed" if insp.fail_count > 0 else "passed"
    db.commit()
    return {"ok": True, "pass_count": insp.pass_count if insp else 0, "fail_count": insp.fail_count if insp else 0}


@router.put("/{project_id}/quality-inspections/{insp_id}")
def update_inspection(project_id: int, insp_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    insp = db.query(QualityInspection).filter(QualityInspection.id == insp_id, QualityInspection.project_id == project_id).first()
    if not insp: raise HTTPException(404)
    for f in ["inspection_date","inspector_name","area_location","inspection_type","status","notes"]:
        if f in body: setattr(insp, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/quality-inspections/{insp_id}")
def delete_inspection(project_id: int, insp_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    insp = db.query(QualityInspection).filter(QualityInspection.id == insp_id, QualityInspection.project_id == project_id).first()
    if insp: db.delete(insp); db.commit()
    return {"ok": True}


# ── Visitor Log ─────────────────────────────────────────────────────────────────

@router.get("/{project_id}/visitors")
def list_visitors(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    rows = db.query(VisitorLog).filter(VisitorLog.project_id == project_id).order_by(VisitorLog.visit_date.desc(), VisitorLog.time_in.desc()).all()
    return [{"id": r.id, "visit_date": r.visit_date, "visitor_name": r.visitor_name,
             "visitor_company": r.visitor_company, "visitor_type": r.visitor_type,
             "purpose": r.purpose, "host_name": r.host_name,
             "time_in": r.time_in, "time_out": r.time_out,
             "badge_number": r.badge_number, "safety_orientation": r.safety_orientation,
             "notes": r.notes} for r in rows]


@router.post("/{project_id}/visitors")
def log_visitor(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    v = VisitorLog(
        org_id=p.org_id, project_id=project_id,
        visit_date=body.get("visit_date", datetime.utcnow().strftime("%Y-%m-%d")),
        visitor_name=body["visitor_name"],
        visitor_company=body.get("visitor_company"),
        visitor_type=body.get("visitor_type", "other"),
        purpose=body.get("purpose"), host_name=body.get("host_name"),
        time_in=body.get("time_in"), time_out=body.get("time_out"),
        badge_number=body.get("badge_number"),
        safety_orientation=body.get("safety_orientation", False),
        notes=body.get("notes"), created_by=user.id,
    )
    db.add(v); db.commit(); db.refresh(v)
    return {"id": v.id, "ok": True}


@router.put("/{project_id}/visitors/{vis_id}")
def update_visitor(project_id: int, vis_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    v = db.query(VisitorLog).filter(VisitorLog.id == vis_id, VisitorLog.project_id == project_id).first()
    if not v: raise HTTPException(404)
    for f in ["visitor_name","visitor_company","visitor_type","purpose","host_name","time_in","time_out","badge_number","safety_orientation","notes"]:
        if f in body: setattr(v, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/visitors/{vis_id}")
def delete_visitor(project_id: int, vis_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    v = db.query(VisitorLog).filter(VisitorLog.id == vis_id, VisitorLog.project_id == project_id).first()
    if v: db.delete(v); db.commit()
    return {"ok": True}


# ── Estimating Lite ─────────────────────────────────────────────────────────────

@router.get("/{project_id}/estimates")
def list_estimates(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    ests = db.query(Estimate).filter(Estimate.project_id == project_id).order_by(Estimate.created_at.desc()).all()
    return [{"id": e.id, "name": e.name, "description": e.description, "status": e.status,
             "version": e.version,
             "total": round(sum(i.total_cost or 0 for i in e.line_items), 2),
             "line_item_count": len(e.line_items),
             "created_at": e.created_at.isoformat()} for e in ests]


@router.post("/{project_id}/estimates")
def create_estimate(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    e = Estimate(org_id=p.org_id, project_id=project_id,
                 name=body["name"], description=body.get("description"),
                 status="draft", created_by=user.id)
    db.add(e); db.commit(); db.refresh(e)
    return {"id": e.id, "ok": True}


@router.get("/{project_id}/estimates/{est_id}/items")
def get_estimate_items(project_id: int, est_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    e = db.query(Estimate).filter(Estimate.id == est_id, Estimate.project_id == project_id).first()
    if not e: raise HTTPException(404)
    items = sorted(e.line_items, key=lambda x: (x.division or "", x.display_order))
    total = sum(i.total_cost or 0 for i in items)
    divisions = {}
    for i in items:
        div = i.division or "General"
        if div not in divisions: divisions[div] = 0
        divisions[div] += i.total_cost or 0
    return {
        "estimate": {"id": e.id, "name": e.name, "status": e.status, "total": round(total, 2)},
        "items": [{"id": i.id, "division": i.division, "description": i.description,
                   "quantity": i.quantity, "unit": i.unit, "unit_cost": i.unit_cost,
                   "total_cost": i.total_cost, "subcontracted": i.subcontracted,
                   "notes": i.notes, "display_order": i.display_order} for i in items],
        "by_division": {k: round(v, 2) for k, v in divisions.items()},
        "total": round(total, 2),
    }


@router.post("/{project_id}/estimates/{est_id}/items")
def add_estimate_item(project_id: int, est_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    e = db.query(Estimate).filter(Estimate.id == est_id, Estimate.project_id == project_id).first()
    if not e: raise HTTPException(404)
    qty = body.get("quantity")
    unit_cost = body.get("unit_cost")
    total = body.get("total_cost") or (qty * unit_cost if qty and unit_cost else None)
    item = EstimateLineItem(
        estimate_id=est_id, org_id=p.org_id, project_id=project_id,
        division=body.get("division"), description=body["description"],
        quantity=qty, unit=body.get("unit"), unit_cost=unit_cost, total_cost=total,
        cost_category_id=body.get("cost_category_id"),
        labour_pct=body.get("labour_pct"), material_pct=body.get("material_pct"),
        subcontracted=body.get("subcontracted", False),
        notes=body.get("notes"), display_order=body.get("display_order", 100),
    )
    db.add(item); db.commit(); db.refresh(item)
    return {"id": item.id, "ok": True}


@router.put("/{project_id}/estimates/{est_id}/items/{item_id}")
def update_estimate_item(project_id: int, est_id: int, item_id: int, body: dict,
                         db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    item = db.query(EstimateLineItem).filter(EstimateLineItem.id == item_id, EstimateLineItem.estimate_id == est_id).first()
    if not item: raise HTTPException(404)
    for f in ["division","description","quantity","unit","unit_cost","total_cost","subcontracted","notes","display_order","cost_category_id"]:
        if f in body: setattr(item, f, body[f])
    if item.quantity and item.unit_cost and not body.get("total_cost"):
        item.total_cost = item.quantity * item.unit_cost
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/estimates/{est_id}/items/{item_id}")
def delete_estimate_item(project_id: int, est_id: int, item_id: int,
                         db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    item = db.query(EstimateLineItem).filter(EstimateLineItem.id == item_id, EstimateLineItem.estimate_id == est_id).first()
    if item: db.delete(item); db.commit()
    return {"ok": True}


@router.post("/{project_id}/estimates/{est_id}/convert-to-budget")
def convert_to_budget(project_id: int, est_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    """Convert estimate totals into project cost categories (creates or updates)."""
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    e = db.query(Estimate).filter(Estimate.id == est_id, Estimate.project_id == project_id).first()
    if not e: raise HTTPException(404)
    # Group items by division → create cost categories
    divisions = {}
    for item in e.line_items:
        div = item.division or "General"
        if div not in divisions: divisions[div] = 0
        divisions[div] += item.total_cost or 0
    created = 0; updated = 0
    for div, total in divisions.items():
        existing = db.query(CostCategory).filter(
            CostCategory.project_id == project_id, CostCategory.name == div).first()
        if existing:
            existing.budget = total; updated += 1
        else:
            cat = CostCategory(project_id=project_id, name=div, budget=total)
            db.add(cat); created += 1
    # Update project total budget
    p.total_budget = sum(divisions.values())
    e.status = "approved"
    db.commit()
    return {"ok": True, "created_categories": created, "updated_categories": updated,
            "total_budget": round(p.total_budget, 2)}
