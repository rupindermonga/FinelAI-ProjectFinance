"""
Phase 10 — Adjudication Workflow (Prompt Payment Disputes)
Covers all Canadian provinces implementing statutory adjudication.
ON: 28-day determination; AB: 30 days; BC: 28 days; NS: 28 days; MB/SK/NB/NL/PEI/NT/YT/NU: various.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, require_project_access, FINANCE_READ_ROLES
from ..models import AdjudicationCase, AdjudicationDocument, User

router = APIRouter(prefix="/api", tags=["adjudication"])


# Province adjudication rules — days for determination after adjudicator appointment
PROVINCE_RULES = {
    "ON": {"determination_days": 28, "act": "Construction Act, SO 1990 c C.30"},
    "AB": {"determination_days": 30, "act": "Prompt Payment and Construction Lien Act, SA 2020 c P-26.5"},
    "BC": {"determination_days": 28, "act": "Builders Lien Act, RSBC 1996 c 41 / Bill 18"},
    "SK": {"determination_days": 28, "act": "The Builders' Lien (Prompt Payment) Amendment Act"},
    "MB": {"determination_days": 28, "act": "Builders' Liens Act, CCSM c B91"},
    "NS": {"determination_days": 28, "act": "Builders' Lien Act, RSNS 1989 c 277"},
    "NB": {"determination_days": 28, "act": "Construction Remedies Act, SNB 2022 c 22"},
    "NL": {"determination_days": 28, "act": "Mechanics' Lien Act, RSNL 1990 c M-3"},
    "PEI": {"determination_days": 28, "act": "Mechanics' Lien Act, RSPEI 1988 c M-4"},
    "QC": {"determination_days": 90, "act": "An Act respecting contracting by public bodies"},
    "YT": {"determination_days": 28, "act": "Builders' Liens Act, RSY 2002 c 15"},
    "NT": {"determination_days": 28, "act": "Mechanics' Lien Act, RSNWT 1988 c M-7"},
    "NU": {"determination_days": 28, "act": "Mechanics' Lien Act (as adopted)"},
}


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@router.get("/project/{project_id}/adjudications")
def list_adjudications(project_id: int, db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    rows = (db.query(AdjudicationCase)
            .filter(AdjudicationCase.project_id == project_id,
                    AdjudicationCase.org_id == current_user.org_id)
            .order_by(AdjudicationCase.created_at.desc()).all())
    out = []
    for r in rows:
        d = {k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"}
        d["province_rules"] = PROVINCE_RULES.get(r.province, PROVINCE_RULES["ON"])
        out.append(d)
    return out


@router.post("/project/{project_id}/adjudications")
def create_adjudication(project_id: int, body: dict,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    province = body.get("province", "ON")
    rules = PROVINCE_RULES.get(province, PROVINCE_RULES["ON"])

    # Auto-compute determination_deadline from adjudicator_appointed_date
    det_deadline = None
    appt_date_str = body.get("adjudicator_appointed_date")
    if appt_date_str:
        try:
            appt_dt = datetime.strptime(appt_date_str, "%Y-%m-%d")
            det_deadline = (appt_dt + timedelta(days=rules["determination_days"])).strftime("%Y-%m-%d")
        except Exception:
            pass

    case = AdjudicationCase(
        org_id=current_user.org_id, project_id=project_id,
        created_by=current_user.id,
        determination_deadline=det_deadline,
        **{k: v for k, v in body.items() if hasattr(AdjudicationCase, k) and k not in ("id", "created_at")}
    )
    if det_deadline and not body.get("determination_deadline"):
        case.determination_deadline = det_deadline
    db.add(case)
    db.commit()
    db.refresh(case)
    return {"id": case.id, "determination_deadline": case.determination_deadline, "msg": "adjudication case created"}


@router.put("/project/{project_id}/adjudications/{case_id}")
def update_adjudication(project_id: int, case_id: int, body: dict,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    case = db.query(AdjudicationCase).filter(
        AdjudicationCase.id == case_id,
        AdjudicationCase.org_id == current_user.org_id
    ).first()
    if not case:
        raise HTTPException(404)
    for k, v in body.items():
        if hasattr(case, k):
            setattr(case, k, v)
    # Re-compute deadline if appointment date changed
    if "adjudicator_appointed_date" in body and body["adjudicator_appointed_date"]:
        province = body.get("province", case.province or "ON")
        rules = PROVINCE_RULES.get(province, PROVINCE_RULES["ON"])
        try:
            appt_dt = datetime.strptime(body["adjudicator_appointed_date"], "%Y-%m-%d")
            case.determination_deadline = (appt_dt + timedelta(days=rules["determination_days"])).strftime("%Y-%m-%d")
        except Exception:
            pass
    db.commit()
    return {"msg": "updated", "determination_deadline": case.determination_deadline}


@router.delete("/project/{project_id}/adjudications/{case_id}")
def delete_adjudication(project_id: int, case_id: int,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    case = db.query(AdjudicationCase).filter(
        AdjudicationCase.id == case_id,
        AdjudicationCase.org_id == current_user.org_id
    ).first()
    if not case:
        raise HTTPException(404)
    db.delete(case)
    db.commit()
    return {"msg": "deleted"}


# ─── Adjudication Documents ───────────────────────────────────────────────────

@router.get("/project/{project_id}/adjudications/{case_id}/documents")
def list_adj_documents(project_id: int, case_id: int,
                       db: Session = Depends(get_db),
                       current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    rows = (db.query(AdjudicationDocument)
            .filter(AdjudicationDocument.case_id == case_id,
                    AdjudicationDocument.org_id == current_user.org_id)
            .order_by(AdjudicationDocument.submit_date).all())
    return [{k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"} for r in rows]


@router.post("/project/{project_id}/adjudications/{case_id}/documents")
def create_adj_document(project_id: int, case_id: int, body: dict,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    doc = AdjudicationDocument(
        case_id=case_id, org_id=current_user.org_id,
        **{k: v for k, v in body.items() if hasattr(AdjudicationDocument, k)}
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return {"id": doc.id, "msg": "created"}


@router.delete("/project/{project_id}/adjudications/{case_id}/documents/{doc_id}")
def delete_adj_document(project_id: int, case_id: int, doc_id: int,
                        db: Session = Depends(get_db),
                        current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id, FINANCE_READ_ROLES)
    require_project_access(db, project_id, current_user.org_id)
    doc = db.query(AdjudicationDocument).filter(
        AdjudicationDocument.id == doc_id,
        AdjudicationDocument.org_id == current_user.org_id
    ).first()
    if not doc:
        raise HTTPException(404)
    db.delete(doc)
    db.commit()
    return {"msg": "deleted"}


@router.get("/adjudication/province-rules")
def get_province_rules():
    """Return all province adjudication rules (no auth needed — public reference)."""
    return PROVINCE_RULES
