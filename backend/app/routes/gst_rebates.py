"""
Phase 10 — GST/HST Rebate Tracker
- New Housing Rebate (GST190): up to 36% of GST paid, max $6,300
- NRRP Rebate (GST524): rental residential units
- Purpose-Built Rental Housing Rebate (2024+): 100% GST/HST rebate
- Owner-built homes (GST191)
- PST/QST reference data for all provinces
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import SessionLocal
from ..dependencies import get_current_user, require_org_member, require_project_access
from ..models import GSTRebateApplication, User

router = APIRouter(prefix="/api", tags=["gst-rebates"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ─── Canadian Tax Reference Data ──────────────────────────────────────────────

TAX_REFERENCE = {
    "ON": {
        "gst_hst_rate": 13.0, "type": "HST", "pst_rate": None,
        "construction_notes": "HST on materials + labour. New housing rebate applies to new homes <$450K. Purpose-built rental 100% rebate (2024). NRRP rebate for new residential rentals.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "BC": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": 7.0,
        "construction_notes": "5% GST + 7% PST. PST exempt on real property contracts (labour). PST applies to materials. New housing rebate on GST portion. No HST since 2013.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "AB": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": None,
        "construction_notes": "5% GST only — no provincial sales tax. Lowest tax burden in Canada for construction.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "QC": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": 9.975,
        "construction_notes": "5% GST + 9.975% QST. QST applies to construction services and materials. Separate QST new housing rebate administered by Revenu Québec.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "MB": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": 7.0,
        "construction_notes": "5% GST + 7% RST (Retail Sales Tax). RST applies to construction materials; services may be exempt. Check Manitoba Finance for current exemptions.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "SK": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": 6.0,
        "construction_notes": "5% GST + 6% PST. PST applies to materials, equipment rentals. Labour generally exempt from PST in SK.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "NS": {
        "gst_hst_rate": 15.0, "type": "HST", "pst_rate": None,
        "construction_notes": "15% HST (highest HST in Canada). New housing rebate on federal 5% portion only. Nova Scotia has separate provincial new housing rebate.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "NB": {
        "gst_hst_rate": 15.0, "type": "HST", "pst_rate": None,
        "construction_notes": "15% HST. New housing rebate applies on federal component. NB has no separate provincial rebate program.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "NL": {
        "gst_hst_rate": 15.0, "type": "HST", "pst_rate": None,
        "construction_notes": "15% HST. Same rebate rules as federal. Newfoundland no longer has separate housing rebate beyond federal.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "PEI": {
        "gst_hst_rate": 15.0, "type": "HST", "pst_rate": None,
        "construction_notes": "15% HST. PEI joined HST in 2013. Federal new housing rebate applies. No separate PEI housing rebate.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "YT": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": None,
        "construction_notes": "5% GST. No territorial sales tax. Very few construction-specific rules.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "NT": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": None,
        "construction_notes": "5% GST. No territorial sales tax.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
    "NU": {
        "gst_hst_rate": 5.0, "type": "GST", "pst_rate": None,
        "construction_notes": "5% GST. No territorial sales tax. Limited construction activity.",
        "new_housing_rebate_max": 6300, "new_housing_rebate_pct": 36, "new_housing_rebate_threshold": 450000,
        "nrrp_rebate": True, "pbr_rebate_100pct": True,
    },
}


def _calculate_rebate(rebate_type: str, purchase_price: float, gst_paid: float,
                      hst_paid: float, province: str, is_purpose_built_rental: bool) -> dict:
    """Compute estimated rebate amount based on rebate type and inputs."""
    tax_ref = TAX_REFERENCE.get(province, TAX_REFERENCE["ON"])
    total_tax_paid = (gst_paid or 0) + (hst_paid or 0)
    result = {"estimated_rebate": 0.0, "rebate_pct": 0.0, "eligible_amount": total_tax_paid, "notes": ""}

    if is_purpose_built_rental and rebate_type in ("purpose_built_rental", "nrrp"):
        # 2024+ Purpose-Built Rental Housing Rebate: 100% of GST/HST
        result["rebate_pct"] = 100.0
        result["estimated_rebate"] = total_tax_paid
        result["notes"] = "100% GST/HST rebate under Purpose-Built Rental Housing Rebate (Fall 2023 federal announcement, effective Sept 2023)."
    elif rebate_type == "new_housing":
        threshold = tax_ref["new_housing_rebate_threshold"]
        max_rebate = tax_ref["new_housing_rebate_max"]
        if purchase_price and purchase_price >= threshold:
            result["rebate_pct"] = 0.0
            result["estimated_rebate"] = 0.0
            result["notes"] = f"No rebate — purchase price ≥ ${threshold:,.0f} threshold."
        else:
            # Linear phase-out between $350K–$450K
            if purchase_price and purchase_price > 350000:
                factor = (threshold - purchase_price) / (threshold - 350000)
                est = min(max_rebate, total_tax_paid * 0.36) * factor
            else:
                est = min(max_rebate, total_tax_paid * 0.36)
            result["rebate_pct"] = 36.0
            result["estimated_rebate"] = round(est, 2)
            result["notes"] = f"New Housing Rebate (GST190): 36% of federal GST paid, max ${max_rebate:,.0f}."
    elif rebate_type == "nrrp":
        # NRRP: similar 36% rebate on GST portion for rental units
        est = min(6300, total_tax_paid * 0.36)
        result["rebate_pct"] = 36.0
        result["estimated_rebate"] = round(est, 2)
        result["notes"] = "NRRP Rebate (GST524): 36% of GST paid for new residential rental property."
    elif rebate_type == "owner_built":
        est = min(6300, total_tax_paid * 0.36)
        result["rebate_pct"] = 36.0
        result["estimated_rebate"] = round(est, 2)
        result["notes"] = "Owner-Built New Home Rebate (GST191): 36% of GST paid on materials/services."

    return result


@router.get("/tax/province-reference")
def get_tax_reference():
    """Return GST/HST/PST rates and notes for all 13 provinces/territories."""
    return TAX_REFERENCE


@router.post("/tax/calculate-rebate")
def calculate_rebate(body: dict):
    """Quick rebate estimator — no auth required."""
    rebate_type = body.get("rebate_type", "new_housing")
    purchase_price = body.get("purchase_price") or 0
    gst_paid = body.get("gst_paid") or 0
    hst_paid = body.get("hst_paid") or 0
    province = body.get("province", "ON")
    is_pbr = body.get("is_purpose_built_rental", False)
    return _calculate_rebate(rebate_type, purchase_price, gst_paid, hst_paid, province, is_pbr)


@router.get("/project/{project_id}/gst-rebates")
def list_gst_rebates(project_id: int, db: Session = Depends(get_db),
                     current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    rows = (db.query(GSTRebateApplication)
            .filter(GSTRebateApplication.project_id == project_id,
                    GSTRebateApplication.org_id == current_user.org_id)
            .order_by(GSTRebateApplication.created_at.desc()).all())
    return [{k: v for k, v in r.__dict__.items() if k != "_sa_instance_state"} for r in rows]


@router.post("/project/{project_id}/gst-rebates")
def create_gst_rebate(project_id: int, body: dict,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    # Auto-compute estimated_rebate
    calc = _calculate_rebate(
        body.get("rebate_type", "new_housing"),
        body.get("purchase_price", 0),
        body.get("gst_paid", 0),
        body.get("hst_paid", 0),
        body.get("province", "ON"),
        body.get("is_purpose_built_rental", False),
    )
    rebate = GSTRebateApplication(
        org_id=current_user.org_id, project_id=project_id,
        created_by=current_user.id,
        estimated_rebate=calc["estimated_rebate"],
        rebate_pct=calc["rebate_pct"],
        eligible_amount=calc["eligible_amount"],
        **{k: v for k, v in body.items() if hasattr(GSTRebateApplication, k) and k not in ("id", "created_at")}
    )
    db.add(rebate)
    db.commit()
    db.refresh(rebate)
    return {"id": rebate.id, "estimated_rebate": rebate.estimated_rebate, "msg": "created"}


@router.put("/project/{project_id}/gst-rebates/{rebate_id}")
def update_gst_rebate(project_id: int, rebate_id: int, body: dict,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    rebate = db.query(GSTRebateApplication).filter(
        GSTRebateApplication.id == rebate_id,
        GSTRebateApplication.org_id == current_user.org_id
    ).first()
    if not rebate:
        raise HTTPException(404)
    for k, v in body.items():
        if hasattr(rebate, k):
            setattr(rebate, k, v)
    # Re-compute if tax amounts changed
    calc = _calculate_rebate(
        rebate.rebate_type, rebate.purchase_price or 0,
        rebate.gst_paid or 0, rebate.hst_paid or 0,
        rebate.province or "ON", rebate.is_purpose_built_rental or False
    )
    rebate.estimated_rebate = calc["estimated_rebate"]
    rebate.rebate_pct = calc["rebate_pct"]
    db.commit()
    return {"msg": "updated", "estimated_rebate": rebate.estimated_rebate}


@router.delete("/project/{project_id}/gst-rebates/{rebate_id}")
def delete_gst_rebate(project_id: int, rebate_id: int,
                      db: Session = Depends(get_db),
                      current_user: User = Depends(get_current_user)):
    require_org_member(db, current_user.org_id, current_user.id)
    require_project_access(db, project_id, current_user.org_id)
    rebate = db.query(GSTRebateApplication).filter(
        GSTRebateApplication.id == rebate_id,
        GSTRebateApplication.org_id == current_user.org_id
    ).first()
    if not rebate:
        raise HTTPException(404)
    db.delete(rebate)
    db.commit()
    return {"msg": "deleted"}
