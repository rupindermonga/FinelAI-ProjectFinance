"""Project finance routes: project CRUD, cost categories, sub-divisions, allocations, payments, dashboard, bookkeeping export."""
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Optional
import io
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter
from datetime import datetime

from ..database import get_db
from ..models import (
    User, Project, SubDivision, CostCategory, CostSubCategory,
    SubDivisionBudget, Invoice, InvoiceAllocation, Payment,
    Draw, Claim, PayrollEntry,
)
from ..schemas import (
    ProjectCreate, ProjectUpdate, ProjectOut,
    SubDivisionOut, CostCategoryOut, CostCategoryCreate, CostCategoryUpdate,
    CostSubCategoryCreate, CostSubCategoryOut,
    SubDivisionBudgetSet, AllocationCreate, AllocationOut,
    PaymentCreate, PaymentOut,
    DrawCreate, DrawUpdate, DrawOut,
    ClaimCreate, ClaimUpdate, ClaimOut,
    InvoiceCostUpdate, PayrollEntryCreate, PayrollEntryUpdate, PayrollEntryOut,
)
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/project", tags=["project"])


# ─── Project resolver dependency ─────────────────────────────────────────────
# Any endpoint that Depends on these automatically accepts ?project_id=N.
# If project_id is omitted, the user's first project is used (backwards compat).

def _get_proj(
    project_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Optional[Project]:
    q = db.query(Project).filter(Project.user_id == current_user.id)
    if project_id:
        q = q.filter(Project.id == project_id)
    return q.order_by(Project.created_at).first()


def _req_proj(proj: Optional[Project] = Depends(_get_proj)) -> Project:
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


# ─── Project CRUD ────────────────────────────────────────────────────────────

@router.get("/list")
def list_projects(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """List all projects for the current user."""
    return db.query(Project).filter(Project.user_id == current_user.id).order_by(Project.created_at).all()


@router.get("", response_model=Optional[ProjectOut])
def get_project(proj: Optional[Project] = Depends(_get_proj)):
    return proj


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Create a new project. Multiple projects per user are allowed."""
    proj = Project(user_id=current_user.id, **body.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.put("", response_model=ProjectOut)
def update_project(body: ProjectUpdate, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    _ALLOWED = {"name", "code", "client", "address", "start_date", "end_date", "total_budget", "currency"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in _ALLOWED:
            setattr(proj, field, value)
    db.commit()
    db.refresh(proj)
    return proj


@router.delete("/{project_id}")
def delete_project(project_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    db.delete(proj)
    db.commit()
    return {"message": "Project deleted"}


# ─── Sub-Divisions ───────────────────────────────────────────────────────────

@router.get("/subdivisions", response_model=List[SubDivisionOut])
def list_subdivisions(proj: Optional[Project] = Depends(_get_proj), db: Session = Depends(get_db)):
    if not proj:
        return []
    return db.query(SubDivision).filter(SubDivision.project_id == proj.id).order_by(SubDivision.display_order).all()


@router.post("/subdivisions", response_model=SubDivisionOut)
def create_subdivision(name: str, description: str = None, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    if not proj:
        raise HTTPException(status_code=404, detail="Create a project first")
    sd = SubDivision(project_id=proj.id, name=name, description=description)
    db.add(sd)
    db.commit()
    db.refresh(sd)
    return sd


# ─── Cost Categories ─────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CostCategoryOut])
def list_cost_categories(proj: Optional[Project] = Depends(_get_proj), db: Session = Depends(get_db)):
    if not proj:
        return []
    return (
        db.query(CostCategory)
        .filter(CostCategory.project_id == proj.id)
        .order_by(CostCategory.display_order)
        .all()
    )


@router.post("/categories", response_model=CostCategoryOut)
def create_cost_category(body: CostCategoryCreate, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    if body.budget < 0:
        raise HTTPException(status_code=400, detail="Budget must be non-negative")
    existing = db.query(CostCategory).filter(CostCategory.project_id == proj.id, CostCategory.name == body.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Category name already exists in this project")
    cat = CostCategory(project_id=proj.id, **body.model_dump())
    db.add(cat)
    db.commit()
    db.refresh(cat)
    return cat


@router.put("/categories/{cat_id}", response_model=CostCategoryOut)
def update_cost_category(cat_id: int, body: CostCategoryUpdate, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    updates = body.model_dump(exclude_unset=True)
    if "budget" in updates and updates["budget"] is not None and updates["budget"] < 0:
        raise HTTPException(status_code=400, detail="Budget must be non-negative")
    _ALLOWED = {"name", "budget"}
    for field, value in updates.items():
        if field in _ALLOWED:
            setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}")
def delete_cost_category(cat_id: int, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    db.delete(cat)
    db.commit()
    return {"message": "Deleted"}


# ─── Cost Sub-Categories ─────────────────────────────────────────────────────

@router.post("/categories/{cat_id}/subcategories", response_model=CostSubCategoryOut)
def create_cost_subcategory(cat_id: int, body: CostSubCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cat = (db.query(CostCategory).join(Project, Project.id == CostCategory.project_id)
            .filter(CostCategory.id == cat_id, Project.user_id == current_user.id).first())
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    sc = CostSubCategory(category_id=cat_id, name=body.name, description=body.description, budget=body.budget)
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


@router.delete("/subcategories/{sc_id}")
def delete_cost_subcategory(sc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    sc = (db.query(CostSubCategory)
          .join(CostCategory, CostCategory.id == CostSubCategory.category_id)
          .join(Project, Project.id == CostCategory.project_id)
          .filter(CostSubCategory.id == sc_id, Project.user_id == current_user.id).first())
    if not sc:
        raise HTTPException(status_code=404)
    db.delete(sc)
    db.commit()
    return {"message": "Deleted"}


# ─── Sub-Division Budgets (for Fiber Build etc.) ─────────────────────────────

@router.put("/categories/{cat_id}/subdivision-budgets")
def set_subdivision_budgets(cat_id: int, budgets: List[SubDivisionBudgetSet], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cat = (db.query(CostCategory).join(Project, Project.id == CostCategory.project_id)
            .filter(CostCategory.id == cat_id, Project.user_id == current_user.id).first())
    if not cat:
        raise HTTPException(status_code=404)
    proj = db.query(Project).filter(Project.id == cat.project_id).first()
    # Upsert budgets — verify each subdivision belongs to this project
    for b in budgets:
        sd = db.query(SubDivision).filter(SubDivision.id == b.subdivision_id, SubDivision.project_id == proj.id).first()
        if not sd:
            raise HTTPException(status_code=404, detail=f"Sub-division {b.subdivision_id} not found in your project")
        if b.budget < 0:
            raise HTTPException(status_code=400, detail="Budget must be non-negative")
        existing = db.query(SubDivisionBudget).filter(
            SubDivisionBudget.category_id == cat_id,
            SubDivisionBudget.subdivision_id == b.subdivision_id
        ).first()
        if existing:
            existing.budget = b.budget
        else:
            db.add(SubDivisionBudget(category_id=cat_id, subdivision_id=b.subdivision_id, budget=b.budget))
    db.commit()
    return {"message": "Budgets updated"}


@router.get("/categories/{cat_id}/subdivision-budgets")
def get_subdivision_budgets(cat_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    cat = (db.query(CostCategory).join(Project, Project.id == CostCategory.project_id)
            .filter(CostCategory.id == cat_id, Project.user_id == current_user.id).first())
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    rows = db.query(SubDivisionBudget).filter(SubDivisionBudget.category_id == cat_id).all()
    return [{"subdivision_id": r.subdivision_id, "budget": r.budget} for r in rows]


# ─── Invoice Allocations ─────────────────────────────────────────────────────

@router.get("/allocations/{invoice_id}", response_model=List[AllocationOut])
def get_allocations(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404)
    allocs = db.query(InvoiceAllocation).filter(InvoiceAllocation.invoice_id == invoice_id).all()
    result = []
    for a in allocs:
        out = AllocationOut(
            id=a.id, invoice_id=a.invoice_id, category_id=a.category_id,
            sub_category_id=a.sub_category_id, subdivision_id=a.subdivision_id,
            percentage=a.percentage, amount=a.amount,
            category_name=a.category.name if a.category else None,
            sub_category_name=a.sub_category.name if a.sub_category else None,
            subdivision_name=a.subdivision.name if a.subdivision else None,
        )
        result.append(out)
    return result


@router.put("/allocations/{invoice_id}")
def set_allocations(invoice_id: int, allocations: List[AllocationCreate], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Replace all allocations for an invoice."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404)
    proj = (db.query(Project).filter(Project.user_id == current_user.id)
            .order_by(Project.created_at).first())

    # Validate individual percentages
    for a in allocations:
        if a.percentage <= 0 or a.percentage > 100:
            raise HTTPException(status_code=400, detail="Each allocation percentage must be between 0 and 100")

    # Validate total percentage
    total_pct = sum(a.percentage for a in allocations)
    if allocations and abs(total_pct - 100.0) > 0.01:
        raise HTTPException(status_code=400, detail=f"Allocation percentages must total 100% (got {total_pct}%)")

    # Validate all referenced cost structures belong to user's project
    for a in allocations:
        cat = db.query(CostCategory).filter(CostCategory.id == a.category_id, CostCategory.project_id == proj.id).first()
        if not cat:
            raise HTTPException(status_code=404, detail=f"Cost category {a.category_id} not found in your project")
        if a.sub_category_id:
            sc = db.query(CostSubCategory).filter(CostSubCategory.id == a.sub_category_id, CostSubCategory.category_id == a.category_id).first()
            if not sc:
                raise HTTPException(status_code=404, detail="Sub-category not found in this category")
        if a.subdivision_id:
            sd = db.query(SubDivision).filter(SubDivision.id == a.subdivision_id, SubDivision.project_id == proj.id).first()
            if not sd:
                raise HTTPException(status_code=404, detail="Sub-division not found in your project")

    # Clear old allocations
    db.query(InvoiceAllocation).filter(InvoiceAllocation.invoice_id == invoice_id).delete()

    # Create new
    invoice_total = inv.total_due or 0.0
    for a in allocations:
        amount = round(invoice_total * a.percentage / 100.0, 2)
        db.add(InvoiceAllocation(
            invoice_id=invoice_id,
            category_id=a.category_id,
            sub_category_id=a.sub_category_id,
            subdivision_id=a.subdivision_id,
            percentage=a.percentage,
            amount=amount,
        ))
    db.commit()
    return {"message": "Allocations saved", "count": len(allocations)}


# ─── Payments ─────────────────────────────────────────────────────────────────

@router.get("/payments/{invoice_id}", response_model=List[PaymentOut])
def list_payments(invoice_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404)
    return db.query(Payment).filter(Payment.invoice_id == invoice_id).order_by(Payment.payment_date).all()


@router.post("/payments", response_model=PaymentOut)
def create_payment(body: PaymentCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    inv = db.query(Invoice).filter(Invoice.id == body.invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invoice not found")
    if body.amount <= 0:
        raise HTTPException(status_code=400, detail="Payment amount must be positive")
    balance = (inv.total_due or 0.0) - (inv.amount_paid or 0.0)
    if balance <= 0:
        raise HTTPException(status_code=400, detail="Invoice is already fully paid")
    if body.amount > balance + 0.01:
        raise HTTPException(status_code=400, detail=f"Payment ${body.amount:.2f} exceeds outstanding balance ${balance:.2f}")

    pmt = Payment(
        invoice_id=body.invoice_id,
        amount=body.amount,
        payment_date=body.payment_date,
        method=body.method,
        reference=body.reference,
        notes=body.notes,
    )
    db.add(pmt)

    # Update invoice payment status
    inv.amount_paid = (inv.amount_paid or 0.0) + body.amount
    total = inv.total_due or 0.0
    if total > 0 and inv.amount_paid >= total - 0.01:
        inv.payment_status = "paid"
    elif inv.amount_paid > 0:
        inv.payment_status = "partially_paid"

    db.commit()
    db.refresh(pmt)
    return pmt


@router.delete("/payments/{payment_id}")
def delete_payment(payment_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    # Join through Invoice to verify ownership in a single query
    pmt = db.query(Payment).join(Invoice).filter(
        Payment.id == payment_id,
        Invoice.user_id == current_user.id,
    ).first()
    if not pmt:
        raise HTTPException(status_code=404, detail="Payment not found")
    inv = db.query(Invoice).filter(Invoice.id == pmt.invoice_id).first()
    if not inv:
        raise HTTPException(status_code=404)

    inv.amount_paid = max(0.0, (inv.amount_paid or 0.0) - pmt.amount)
    if inv.amount_paid <= 0.01:
        inv.payment_status = "unpaid"
        inv.amount_paid = 0.0
    else:
        inv.payment_status = "partially_paid"

    db.delete(pmt)
    db.commit()
    return {"message": "Payment deleted"}


# ─── Draws ───────────────────────────────────────────────────────────────────

def _draw_out(draw, db):
    invs = db.query(Invoice).filter(Invoice.draw_id == draw.id).all()
    total_orig = sum(i.total_due or 0 for i in invs)
    return DrawOut(
        id=draw.id, draw_number=draw.draw_number, fx_rate=draw.fx_rate,
        submission_date=draw.submission_date, status=draw.status,
        notes=draw.notes, created_at=draw.created_at,
        invoice_count=len(invs), total_original=round(total_orig, 2),
        total_cad=round(total_orig * draw.fx_rate, 2),
    )

@router.get("/draws")
def list_draws(proj: Optional[Project] = Depends(_get_proj), db: Session = Depends(get_db)):
    if not proj:
        return []
    draws = db.query(Draw).filter(Draw.project_id == proj.id).order_by(Draw.draw_number).all()
    return [_draw_out(d, db) for d in draws]

@router.post("/draws")
def create_draw(body: DrawCreate, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    existing = db.query(Draw).filter(Draw.project_id == proj.id, Draw.draw_number == body.draw_number).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"Draw {body.draw_number} already exists")
    draw = Draw(project_id=proj.id, **body.model_dump())
    db.add(draw)
    db.commit()
    db.refresh(draw)
    return _draw_out(draw, db)

@router.put("/draws/{draw_id}")
def update_draw(draw_id: int, body: DrawUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    draw = (db.query(Draw).join(Project, Project.id == Draw.project_id)
            .filter(Draw.id == draw_id, Project.user_id == current_user.id).first())
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in {"fx_rate", "submission_date", "status", "notes"}:
            setattr(draw, field, value)
    db.commit()
    db.refresh(draw)
    return _draw_out(draw, db)

@router.delete("/draws/{draw_id}")
def delete_draw(draw_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    draw = (db.query(Draw).join(Project, Project.id == Draw.project_id)
            .filter(Draw.id == draw_id, Project.user_id == current_user.id).first())
    if not draw:
        raise HTTPException(status_code=404)
    db.query(Invoice).filter(Invoice.draw_id == draw_id).update({"draw_id": None})
    db.delete(draw)
    db.commit()
    return {"message": "Draw deleted"}

@router.put("/draws/{draw_id}/invoices")
def assign_invoices_to_draw(draw_id: int, invoice_ids: List[int], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    draw = (db.query(Draw).join(Project, Project.id == Draw.project_id)
            .filter(Draw.id == draw_id, Project.user_id == current_user.id).first())
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    # Unlink all currently linked
    db.query(Invoice).filter(Invoice.draw_id == draw_id).update({"draw_id": None})
    # Link new set
    for iid in invoice_ids:
        inv = db.query(Invoice).filter(Invoice.id == iid, Invoice.user_id == current_user.id).first()
        if inv:
            inv.draw_id = draw_id
    db.commit()
    return _draw_out(draw, db)

@router.get("/draws/{draw_id}/invoices")
def get_draw_invoices(draw_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    draw = (db.query(Draw).join(Project, Project.id == Draw.project_id)
            .filter(Draw.id == draw_id, Project.user_id == current_user.id).first())
    if not draw:
        raise HTTPException(status_code=404)
    invs = db.query(Invoice).filter(Invoice.draw_id == draw_id, Invoice.user_id == current_user.id).all()
    return [{
        "id": i.id, "invoice_number": i.invoice_number, "vendor_name": i.vendor_name,
        "currency": i.currency or "CAD", "total_due": i.total_due or 0,
        "cad_amount": round((i.total_due or 0) * draw.fx_rate, 2) if (i.currency or "CAD").upper() != "CAD" else (i.total_due or 0),
        "original_filename": i.original_filename, "invoice_date": i.invoice_date,
        "billed_to": i.billed_to, "billing_type": i.billing_type, "vendor_on_record": i.vendor_on_record,
    } for i in invs]


# ─── Bulk Approve ────────────────────────────────────────────────────────────

@router.post("/draws/{draw_id}/approve-all")
def bulk_approve_draw(draw_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Approve all invoices in a draw: set lender_approved_amt = lender_submitted_amt, status = approved."""
    draw = (db.query(Draw).join(Project, Project.id == Draw.project_id)
            .filter(Draw.id == draw_id, Project.user_id == current_user.id).first())
    if not draw:
        raise HTTPException(status_code=404, detail="Draw not found")
    invs = db.query(Invoice).filter(Invoice.draw_id == draw_id, Invoice.user_id == current_user.id).all()
    count = 0
    for inv in invs:
        # Auto-calc submitted if not set
        st = inv.subtotal or inv.total_due or 0
        if inv.lender_submitted_amt is None:
            inv.lender_margin_amt = round(st * (inv.lender_margin_pct or 0) / 100, 2)
            inv.lender_submitted_amt = round(st + (inv.lender_margin_amt or 0) + (_calc_lender_tax(inv) if hasattr(inv, 'billing_type') else 0), 2)
        inv.lender_approved_amt = inv.lender_submitted_amt
        inv.lender_status = "approved"
        count += 1
    db.commit()
    return {"message": f"Approved {count} invoices", "count": count}


@router.post("/claims/{claim_id}/approve-all")
def bulk_approve_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Approve all invoices in a claim: set govt_approved_amt = govt_submitted_amt, status = approved."""
    claim = (db.query(Claim).join(Project, Project.id == Claim.project_id)
             .filter(Claim.id == claim_id, Project.user_id == current_user.id).first())
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    invs = db.query(Invoice).filter(_claim_fk(claim) == claim_id, Invoice.user_id == current_user.id).all()
    count = 0
    for inv in invs:
        st = inv.subtotal or inv.total_due or 0
        if inv.govt_submitted_amt is None:
            inv.govt_margin_amt = round(st * (inv.govt_margin_pct or 0) / 100, 2)
            inv.govt_submitted_amt = round(st + (inv.govt_margin_amt or 0), 2)
        inv.govt_approved_amt = inv.govt_submitted_amt
        inv.govt_status = "approved"
        count += 1
    db.commit()
    return {"message": f"Approved {count} invoices", "count": count}


# ─── Claims ──────────────────────────────────────────────────────────────────

def _claim_fk(claim):
    """Return the Invoice FK column for this claim's type."""
    return Invoice.provincial_claim_id if claim.claim_type == "provincial" else Invoice.federal_claim_id

def _claim_fk_name(claim):
    """Return the Invoice FK column name string for this claim's type."""
    return "provincial_claim_id" if claim.claim_type == "provincial" else "federal_claim_id"

def _claim_out(claim, db):
    invs = db.query(Invoice).filter(_claim_fk(claim) == claim.id).all()
    total_orig = sum(i.total_due or 0 for i in invs)
    return ClaimOut(
        id=claim.id, claim_number=claim.claim_number, claim_type=claim.claim_type,
        fx_rate=claim.fx_rate, submission_date=claim.submission_date,
        status=claim.status, notes=claim.notes, created_at=claim.created_at,
        invoice_count=len(invs), total_original=round(total_orig, 2),
        total_cad=round(total_orig * claim.fx_rate, 2),
    )

@router.get("/claims")
def list_claims(claim_type: Optional[str] = None, proj: Optional[Project] = Depends(_get_proj), db: Session = Depends(get_db)):
    if not proj:
        return []
    q = db.query(Claim).filter(Claim.project_id == proj.id)
    if claim_type:
        q = q.filter(Claim.claim_type == claim_type)
    return [_claim_out(c, db) for c in q.order_by(Claim.claim_number).all()]

@router.post("/claims")
def create_claim(body: ClaimCreate, proj: Project = Depends(_req_proj), db: Session = Depends(get_db)):
    if body.claim_type not in ("provincial", "federal"):
        raise HTTPException(status_code=400, detail="claim_type must be 'provincial' or 'federal'")
    existing = db.query(Claim).filter(Claim.project_id == proj.id, Claim.claim_number == body.claim_number, Claim.claim_type == body.claim_type).first()
    if existing:
        raise HTTPException(status_code=400, detail=f"{body.claim_type.title()} Claim {body.claim_number} already exists")
    claim = Claim(project_id=proj.id, **body.model_dump())
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return _claim_out(claim, db)

@router.put("/claims/{claim_id}")
def update_claim(claim_id: int, body: ClaimUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    claim = (db.query(Claim).join(Project, Project.id == Claim.project_id)
             .filter(Claim.id == claim_id, Project.user_id == current_user.id).first())
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in {"fx_rate", "submission_date", "status", "notes"}:
            setattr(claim, field, value)
    db.commit()
    db.refresh(claim)
    return _claim_out(claim, db)

@router.delete("/claims/{claim_id}")
def delete_claim(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    claim = (db.query(Claim).join(Project, Project.id == Claim.project_id)
             .filter(Claim.id == claim_id, Project.user_id == current_user.id).first())
    if not claim:
        raise HTTPException(status_code=404)
    fk_name = _claim_fk_name(claim)
    db.query(Invoice).filter(_claim_fk(claim) == claim_id).update({fk_name: None})
    db.delete(claim)
    db.commit()
    return {"message": "Claim deleted"}

@router.put("/claims/{claim_id}/invoices")
def assign_invoices_to_claim(claim_id: int, invoice_ids: List[int], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    claim = (db.query(Claim).join(Project, Project.id == Claim.project_id)
             .filter(Claim.id == claim_id, Project.user_id == current_user.id).first())
    if not claim:
        raise HTTPException(status_code=404, detail="Claim not found")
    fk_name = _claim_fk_name(claim)
    db.query(Invoice).filter(_claim_fk(claim) == claim_id).update({fk_name: None})
    for iid in invoice_ids:
        inv = db.query(Invoice).filter(Invoice.id == iid, Invoice.user_id == current_user.id).first()
        if inv:
            setattr(inv, fk_name, claim_id)
    db.commit()
    return _claim_out(claim, db)

@router.put("/claims/{claim_id}/copy-from-draw/{draw_id}")
def copy_draw_to_claim(claim_id: int, draw_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Copy all invoices from a draw to a claim (for the 99% overlap case)."""
    draw = (db.query(Draw).join(Project, Project.id == Draw.project_id)
            .filter(Draw.id == draw_id, Project.user_id == current_user.id).first())
    claim = (db.query(Claim).join(Project, Project.id == Claim.project_id)
             .filter(Claim.id == claim_id, Project.user_id == current_user.id).first())
    if not draw or not claim:
        raise HTTPException(status_code=404)
    fk_name = _claim_fk_name(claim)
    draw_invs = db.query(Invoice).filter(Invoice.draw_id == draw_id, Invoice.user_id == current_user.id).all()
    for inv in draw_invs:
        setattr(inv, fk_name, claim_id)
    db.commit()
    return _claim_out(claim, db)

@router.get("/claims/{claim_id}/invoices")
def get_claim_invoices(claim_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    claim = (db.query(Claim).join(Project, Project.id == Claim.project_id)
             .filter(Claim.id == claim_id, Project.user_id == current_user.id).first())
    if not claim:
        raise HTTPException(status_code=404)
    invs = db.query(Invoice).filter(_claim_fk(claim) == claim_id, Invoice.user_id == current_user.id).all()
    return [{
        "id": i.id, "invoice_number": i.invoice_number, "vendor_name": i.vendor_name,
        "currency": i.currency or "CAD", "total_due": i.total_due or 0,
        "cad_amount": round((i.total_due or 0) * claim.fx_rate, 2) if (i.currency or "CAD").upper() != "CAD" else (i.total_due or 0),
        "original_filename": i.original_filename, "invoice_date": i.invoice_date,
        "billed_to": i.billed_to, "billing_type": i.billing_type, "vendor_on_record": i.vendor_on_record,
    } for i in invs]


# ─── FX Rate (Bank of Canada) ───────────────────────────────────────────────

@router.get("/fx-rate")
def get_fx_rate(date: Optional[str] = None):
    """Fetch USD→CAD rate from Bank of Canada for a given date. Falls back to 1.0 on error."""
    import urllib.request, json as _json
    target_date = date or datetime.utcnow().strftime("%Y-%m-%d")
    try:
        url = f"https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date={target_date}&end_date={target_date}"
        with urllib.request.urlopen(url, timeout=5) as resp:
            data = _json.loads(resp.read())
        obs = data.get("observations", [])
        if obs:
            return {"date": target_date, "rate": float(obs[-1]["FXUSDCAD"]["v"]), "source": "bank_of_canada"}
        # If no data for that date (weekend/holiday), try last 5 days
        from datetime import timedelta
        d = datetime.strptime(target_date, "%Y-%m-%d")
        start = (d - timedelta(days=5)).strftime("%Y-%m-%d")
        url2 = f"https://www.bankofcanada.ca/valet/observations/FXUSDCAD/json?start_date={start}&end_date={target_date}"
        with urllib.request.urlopen(url2, timeout=5) as resp:
            data = _json.loads(resp.read())
        obs = data.get("observations", [])
        if obs:
            last = obs[-1]
            return {"date": last["d"], "rate": float(last["FXUSDCAD"]["v"]), "source": "bank_of_canada"}
    except Exception:
        pass
    return {"date": target_date, "rate": 1.0, "source": "fallback"}


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def project_dashboard(proj: Optional[Project] = Depends(_get_proj), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    if not proj:
        return {"project": None}

    categories = (
        db.query(CostCategory)
        .filter(CostCategory.project_id == proj.id)
        .order_by(CostCategory.display_order)
        .all()
    )

    subdivisions = (
        db.query(SubDivision)
        .filter(SubDivision.project_id == proj.id)
        .order_by(SubDivision.display_order)
        .all()
    )

    # Build category summary
    cat_summary = []
    for cat in categories:
        # Total allocated to this category
        alloc_sum = (
            db.query(func.coalesce(func.sum(InvoiceAllocation.amount), 0.0))
            .filter(InvoiceAllocation.category_id == cat.id)
            .scalar()
        )
        # Total paid for invoices allocated to this category
        paid_sum = 0.0
        alloc_rows = db.query(InvoiceAllocation).filter(InvoiceAllocation.category_id == cat.id).all()
        for a in alloc_rows:
            inv = db.query(Invoice).filter(Invoice.id == a.invoice_id).first()
            if inv:
                paid_sum += (inv.amount_paid or 0.0) * (a.percentage / 100.0)

        # Sub-category invoiced/paid amounts
        sc_data = []
        for sc in cat.sub_categories:
            sc_invoiced = (
                db.query(func.coalesce(func.sum(InvoiceAllocation.amount), 0.0))
                .filter(InvoiceAllocation.category_id == cat.id, InvoiceAllocation.sub_category_id == sc.id)
                .scalar()
            )
            sc_paid = sum(
                (db.query(Invoice).filter(Invoice.id == a.invoice_id).first().amount_paid or 0.0) * (a.percentage / 100.0)
                for a in db.query(InvoiceAllocation).filter(
                    InvoiceAllocation.category_id == cat.id, InvoiceAllocation.sub_category_id == sc.id
                ).all()
                if db.query(Invoice).filter(Invoice.id == a.invoice_id).first()
            )
            sc_data.append({
                "id": sc.id, "name": sc.name, "budget": sc.budget or 0,
                "invoiced": round(sc_invoiced, 2), "paid": round(sc_paid, 2),
                "remaining": round((sc.budget or 0) - sc_invoiced, 2),
            })

        pct_burn = round((alloc_sum / cat.budget * 100) if cat.budget else 0, 1)
        cat_data = {
            "id": cat.id,
            "name": cat.name,
            "budget": cat.budget,
            "invoiced": round(alloc_sum, 2),
            "paid": round(paid_sum, 2),
            "remaining": round(cat.budget - alloc_sum, 2),
            "pct_burn": pct_burn,
            "is_per_subdivision": cat.is_per_subdivision,
            "sub_categories": sc_data,
        }

        # Per-subdivision breakdown for Fiber Build
        if cat.is_per_subdivision:
            sd_data = []
            for sd in subdivisions:
                sd_budget_row = db.query(SubDivisionBudget).filter(
                    SubDivisionBudget.category_id == cat.id,
                    SubDivisionBudget.subdivision_id == sd.id,
                ).first()
                sd_budget = sd_budget_row.budget if sd_budget_row else 0.0
                sd_invoiced = (
                    db.query(func.coalesce(func.sum(InvoiceAllocation.amount), 0.0))
                    .filter(
                        InvoiceAllocation.category_id == cat.id,
                        InvoiceAllocation.subdivision_id == sd.id,
                    )
                    .scalar()
                )
                sd_data.append({
                    "subdivision_id": sd.id,
                    "name": sd.name,
                    "budget": sd_budget,
                    "invoiced": round(sd_invoiced, 2),
                    "remaining": round(sd_budget - sd_invoiced, 2),
                })
            cat_data["subdivisions"] = sd_data

        cat_summary.append(cat_data)

    # Overall totals
    total_budget = sum(c["budget"] for c in cat_summary)
    total_invoiced = sum(c["invoiced"] for c in cat_summary)
    total_paid = sum(c["paid"] for c in cat_summary)

    # Invoice counts
    all_invoices = db.query(Invoice).filter(Invoice.user_id == current_user.id, Invoice.status == "processed").all()
    unallocated = 0
    for inv in all_invoices:
        has_alloc = db.query(InvoiceAllocation).filter(InvoiceAllocation.invoice_id == inv.id).count()
        if not has_alloc:
            unallocated += 1

    # Aging buckets
    from datetime import datetime, timedelta
    today = datetime.utcnow().strftime("%Y-%m-%d")
    unpaid = db.query(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
        Invoice.payment_status != "paid",
    ).all()
    aging = {"current": 0, "over_30": 0, "over_60": 0, "over_90": 0}
    for inv in unpaid:
        due = inv.due_date or inv.invoice_date
        if not due:
            aging["current"] += (inv.total_due or 0.0)
            continue
        try:
            days = (datetime.strptime(today, "%Y-%m-%d") - datetime.strptime(due, "%Y-%m-%d")).days
        except ValueError:
            days = 0
        amt = (inv.total_due or 0.0) - (inv.amount_paid or 0.0)
        if days > 90:
            aging["over_90"] += amt
        elif days > 60:
            aging["over_60"] += amt
        elif days > 30:
            aging["over_30"] += amt
        else:
            aging["current"] += amt

    # Draws summary
    draws = db.query(Draw).filter(Draw.project_id == proj.id).order_by(Draw.draw_number).all()
    draws_summary = [_draw_out(d, db).model_dump() for d in draws]

    # Claims summary
    prov_claims = db.query(Claim).filter(Claim.project_id == proj.id, Claim.claim_type == "provincial").order_by(Claim.claim_number).all()
    fed_claims = db.query(Claim).filter(Claim.project_id == proj.id, Claim.claim_type == "federal").order_by(Claim.claim_number).all()

    # Unassigned to draws/claims
    no_draw = db.query(Invoice).filter(Invoice.user_id == current_user.id, Invoice.status == "processed", Invoice.draw_id.is_(None)).count()
    no_prov = db.query(Invoice).filter(Invoice.user_id == current_user.id, Invoice.status == "processed", Invoice.provincial_claim_id.is_(None)).count()
    no_fed = db.query(Invoice).filter(Invoice.user_id == current_user.id, Invoice.status == "processed", Invoice.federal_claim_id.is_(None)).count()

    # Cost tracking summary (4 views)
    all_processed = db.query(Invoice).filter(Invoice.user_id == current_user.id, Invoice.status == "processed").all()
    committed_total = sum(i.received_total or i.total_due or 0 for i in all_processed)
    lender_approved = sum(i.lender_approved_amt or 0 for i in all_processed)
    lender_pending = sum(i.lender_submitted_amt or 0 for i in all_processed if i.lender_status == "pending")
    lender_rejected = sum(i.lender_submitted_amt or 0 for i in all_processed if i.lender_status == "rejected")
    govt_approved = sum(i.govt_approved_amt or 0 for i in all_processed)
    govt_pending = sum(i.govt_submitted_amt or 0 for i in all_processed if i.govt_status == "pending")
    govt_rejected = sum(i.govt_submitted_amt or 0 for i in all_processed if i.govt_status == "rejected")

    # Payroll summary
    payroll_entries = db.query(PayrollEntry).filter(PayrollEntry.user_id == current_user.id, PayrollEntry.status == "processed").all()
    payroll_committed = sum(p.gross_pay or 0 for p in payroll_entries)
    payroll_lender_approved = sum(p.lender_approved_amt or 0 for p in payroll_entries)
    payroll_govt_approved = sum(p.govt_approved_amt or 0 for p in payroll_entries)

    return {
        "project": ProjectOut.model_validate(proj).model_dump(),
        "total_budget": total_budget,
        "total_invoiced": round(total_invoiced, 2),
        "total_paid": round(total_paid, 2),
        "total_remaining": round(total_budget - total_invoiced, 2),
        "categories": cat_summary,
        "unallocated_invoices": unallocated,
        "aging": {k: round(v, 2) for k, v in aging.items()},
        "draws": draws_summary,
        "provincial_claims": [_claim_out(c, db).model_dump() for c in prov_claims],
        "federal_claims": [_claim_out(c, db).model_dump() for c in fed_claims],
        "invoices_without_draw": no_draw,
        "invoices_without_claim": no_prov + no_fed,
        # Cost tracking 4-view
        "cost_tracking": {
            "committed": round(committed_total + payroll_committed, 2),
            "lender": {
                "approved": round(lender_approved + payroll_lender_approved, 2),
                "pending": round(lender_pending, 2),
                "rejected": round(lender_rejected, 2),
            },
            "govt": {
                "approved": round(govt_approved + payroll_govt_approved, 2),
                "pending": round(govt_pending, 2),
                "rejected": round(govt_rejected, 2),
            },
            "net_position": {
                "committed": round(committed_total + payroll_committed, 2),
                "recovered_lender": round(lender_approved + payroll_lender_approved, 2),
                "recovered_govt": round(govt_approved + payroll_govt_approved, 2),
                "out_of_pocket": round((committed_total + payroll_committed) - (lender_approved + payroll_lender_approved) - (govt_approved + payroll_govt_approved), 2),
            },
            "payroll_committed": round(payroll_committed, 2),
            "payroll_entries_count": len(payroll_entries),
        },
    }


# ─── Invoice Cost Update ─────────────────────────────────────────────────────

# VoR → tax jurisdiction mapping
_QUEBEC_VORS = {"digicom", "digicom inc", "digicom inc."}

def _calc_lender_tax(invoice):
    """Recalculate lender tax based on VoR province."""
    st = invoice.subtotal or invoice.total_due or 0
    margin = invoice.lender_margin_amt or 0
    base = st + margin
    vor = (invoice.vendor_on_record or "").strip().lower()
    if invoice.billing_type == "direct":
        return invoice.tax_total or 0  # pass through
    if vor in _QUEBEC_VORS:
        return round(base * 0.14975, 2)  # GST 5% + QST 9.975%
    return round(base * 0.13, 2)  # HST 13% (Ontario)


@router.put("/invoices/{invoice_id}/cost")
def update_invoice_cost(invoice_id: int, body: InvoiceCostUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Update billing/cost fields on an invoice."""
    inv = db.query(Invoice).filter(Invoice.id == invoice_id, Invoice.user_id == current_user.id).first()
    if not inv:
        raise HTTPException(status_code=404)
    allowed = {"lender_margin_pct", "govt_margin_pct", "lender_submitted_amt", "lender_approved_amt",
               "lender_status", "govt_submitted_amt", "govt_approved_amt", "govt_status"}
    data = body.model_dump(exclude_unset=True)
    # Validate margin percentages
    for pct_field in ("lender_margin_pct", "govt_margin_pct"):
        if pct_field in data and data[pct_field] is not None:
            if data[pct_field] < 0 or data[pct_field] > 200:
                raise HTTPException(status_code=400, detail=f"{pct_field} must be between 0 and 200")
    # Validate amounts are non-negative
    for amt_field in ("lender_submitted_amt", "lender_approved_amt", "govt_submitted_amt", "govt_approved_amt"):
        if amt_field in data and data[amt_field] is not None and data[amt_field] < 0:
            raise HTTPException(status_code=400, detail=f"{amt_field} cannot be negative")
    # Validate status values
    valid_statuses = {"pending", "approved", "partial", "rejected"}
    for status_field in ("lender_status", "govt_status"):
        if status_field in data and data[status_field] is not None and data[status_field] not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"{status_field} must be one of: {', '.join(valid_statuses)}")
    for field, value in data.items():
        if field in allowed:
            setattr(inv, field, value)

    # Recalculate margins and tax
    st = inv.subtotal or inv.total_due or 0
    if inv.lender_margin_pct is not None:
        inv.lender_margin_amt = round(st * (inv.lender_margin_pct or 0) / 100, 2)
    if inv.govt_margin_pct is not None:
        inv.govt_margin_amt = round(st * (inv.govt_margin_pct or 0) / 100, 2)
    inv.received_total = inv.total_due
    inv.lender_tax_amt = _calc_lender_tax(inv)
    # Auto-calc submitted amounts if not manually set
    if inv.lender_submitted_amt is None:
        inv.lender_submitted_amt = round(st + (inv.lender_margin_amt or 0) + (inv.lender_tax_amt or 0), 2)
    if inv.govt_submitted_amt is None:
        inv.govt_submitted_amt = round(st + (inv.govt_margin_amt or 0), 2)
    db.commit()
    db.refresh(inv)
    return {"message": "Cost updated", "id": inv.id}


# ─── Payroll CRUD ────────────────────────────────────────────────────────────

def _calc_payroll(entry: PayrollEntry):
    """Calculate derived payroll fields."""
    entry.eligible_days = (entry.working_days or 0) - (entry.statutory_holidays or 0)
    if entry.eligible_days and entry.eligible_days > 0:
        entry.daily_rate = round((entry.gross_pay or 0) / entry.eligible_days, 2)
    else:
        entry.daily_rate = 0
    entry.lender_billable = entry.gross_pay  # lender approves full gross
    non_claimable = (entry.cpp or 0) + (entry.ei or 0) + (entry.insurance or 0) + (entry.holiday_pay or 0)
    entry.govt_billable = round((entry.gross_pay or 0) - non_claimable, 2)


@router.get("/payroll")
def list_payroll(proj: Optional[Project] = Depends(_get_proj), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    q = db.query(PayrollEntry).filter(PayrollEntry.user_id == current_user.id)
    if proj:
        q = q.filter(PayrollEntry.project_id == proj.id)
    return [PayrollEntryOut.model_validate(e) for e in q.order_by(PayrollEntry.pay_period_start.desc()).all()]


def _validate_payroll(body):
    """Reject negative monetary values in payroll entries."""
    for field in ("gross_pay", "cpp", "ei", "income_tax", "insurance", "holiday_pay", "other_deductions"):
        val = getattr(body, field, None) if hasattr(body, field) else body.get(field) if isinstance(body, dict) else None
        if val is not None and val < 0:
            raise HTTPException(status_code=400, detail=f"{field} cannot be negative")


@router.post("/payroll")
def create_payroll(body: PayrollEntryCreate, proj: Project = Depends(_req_proj), db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _validate_payroll(body)
    entry = PayrollEntry(user_id=current_user.id, project_id=proj.id, status="processed")
    for field, value in body.model_dump().items():
        if hasattr(entry, field):
            setattr(entry, field, value)
    _calc_payroll(entry)
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return PayrollEntryOut.model_validate(entry)


@router.put("/payroll/{entry_id}")
def update_payroll(entry_id: int, body: PayrollEntryUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    _validate_payroll(body)
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == entry_id, PayrollEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404)
    allowed = {"employee_name", "company_name", "gross_pay", "cpp", "ei", "income_tax", "insurance",
               "holiday_pay", "working_days", "statutory_holidays", "province",
               "lender_submitted_amt", "lender_approved_amt", "lender_status",
               "govt_submitted_amt", "govt_approved_amt", "govt_status",
               "draw_id", "provincial_claim_id", "federal_claim_id"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in allowed:
            setattr(entry, field, value)
    _calc_payroll(entry)
    db.commit()
    db.refresh(entry)
    return PayrollEntryOut.model_validate(entry)


@router.delete("/payroll/{entry_id}")
def delete_payroll(entry_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    entry = db.query(PayrollEntry).filter(PayrollEntry.id == entry_id, PayrollEntry.user_id == current_user.id).first()
    if not entry:
        raise HTTPException(status_code=404)
    db.delete(entry)
    db.commit()
    return {"message": "Payroll entry deleted"}


# ─── Bookkeeping Export ──────────────────────────────────────────────────────

def _auth_export(authorization: str, db: Session) -> User:
    from ..dependencies import SECRET_KEY, ALGORITHM
    from jose import jwt
    if not authorization or not authorization.startswith("Bearer "):
        raise ValueError("missing token")
    payload = jwt.decode(authorization[7:], SECRET_KEY, algorithms=[ALGORITHM])
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
    if not user or not user.is_active:
        raise ValueError("invalid")
    return user


@router.get("/export/bookkeeping")
def export_bookkeeping(
    entity: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db),
):
    """Export project finance data as Excel workbook for bookkeeping."""
    try:
        current_user = _auth_export(authorization, db)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid or missing token")

    proj = (db.query(Project).filter(Project.user_id == current_user.id)
            .order_by(Project.created_at).first())
    if not proj:
        raise HTTPException(status_code=404, detail="No project found")

    header_font = Font(bold=True, color="FFFFFF")
    header_fill = PatternFill(start_color="1E3A5F", end_color="1E3A5F", fill_type="solid")
    alt_fill = PatternFill(start_color="F0F4F8", end_color="F0F4F8", fill_type="solid")

    wb = openpyxl.Workbook()

    # ── Sheet 1: Cost Summary ────────────────────────────────────────────────
    ws1 = wb.active
    ws1.title = "Cost Summary"
    headers = ["Category", "Budget", "Invoiced", "Paid", "Remaining", "% Used"]
    for i, h in enumerate(headers, 1):
        c = ws1.cell(row=1, column=i, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")

    cats = db.query(CostCategory).filter(CostCategory.project_id == proj.id).order_by(CostCategory.display_order).all()
    row = 2
    for cat in cats:
        invoiced = db.query(func.coalesce(func.sum(InvoiceAllocation.amount), 0.0)).filter(InvoiceAllocation.category_id == cat.id).scalar()
        paid = 0.0
        for a in db.query(InvoiceAllocation).filter(InvoiceAllocation.category_id == cat.id).all():
            inv = db.query(Invoice).filter(Invoice.id == a.invoice_id).first()
            if inv:
                paid += (inv.amount_paid or 0) * (a.percentage / 100)
        remaining = cat.budget - invoiced
        pct = (invoiced / cat.budget * 100) if cat.budget else 0
        ws1.cell(row=row, column=1, value=cat.name)
        ws1.cell(row=row, column=2, value=round(cat.budget, 2))
        ws1.cell(row=row, column=3, value=round(invoiced, 2))
        ws1.cell(row=row, column=4, value=round(paid, 2))
        ws1.cell(row=row, column=5, value=round(remaining, 2))
        ws1.cell(row=row, column=6, value=round(pct, 1))
        if row % 2 == 0:
            for col in range(1, 7):
                ws1.cell(row=row, column=col).fill = alt_fill
        row += 1
    for i in range(1, 7):
        ws1.column_dimensions[get_column_letter(i)].width = 20

    # ── Sheet 2: Invoice Register ────────────────────────────────────────────
    ws2 = wb.create_sheet("Invoice Register")
    inv_headers = ["Invoice #", "Date", "Due Date", "Vendor", "Billed To", "Billing Type",
                   "Vendor on Record", "Amount", "Paid", "Balance", "Payment Status",
                   "Cost Category", "Sub-Category", "Sub-Division", "Allocation %", "Aging Days"]
    for i, h in enumerate(inv_headers, 1):
        c = ws2.cell(row=1, column=i, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")

    invoices_q = db.query(Invoice).filter(
        Invoice.user_id == current_user.id, Invoice.status == "processed"
    )
    if entity:
        invoices_q = invoices_q.filter(Invoice.billed_to.ilike(f"%{entity}%"))
    invoices = invoices_q.order_by(Invoice.invoice_date.desc()).all()

    today_str = datetime.utcnow().strftime("%Y-%m-%d")
    row = 2
    for inv in invoices:
        allocs = db.query(InvoiceAllocation).filter(InvoiceAllocation.invoice_id == inv.id).all()
        if not allocs:
            allocs = [None]  # still show the invoice even if unallocated

        for alloc in allocs:
            due = inv.due_date or inv.invoice_date
            try:
                aging_days = (datetime.strptime(today_str, "%Y-%m-%d") - datetime.strptime(due, "%Y-%m-%d")).days if due else 0
            except ValueError:
                aging_days = 0

            ws2.cell(row=row, column=1, value=inv.invoice_number)
            ws2.cell(row=row, column=2, value=inv.invoice_date)
            ws2.cell(row=row, column=3, value=inv.due_date)
            ws2.cell(row=row, column=4, value=inv.vendor_name)
            ws2.cell(row=row, column=5, value=inv.billed_to)
            ws2.cell(row=row, column=6, value=inv.billing_type)
            ws2.cell(row=row, column=7, value=inv.vendor_on_record)
            ws2.cell(row=row, column=8, value=round(inv.total_due or 0, 2))
            ws2.cell(row=row, column=9, value=round(inv.amount_paid or 0, 2))
            ws2.cell(row=row, column=10, value=round((inv.total_due or 0) - (inv.amount_paid or 0), 2))
            ws2.cell(row=row, column=11, value=inv.payment_status or "unpaid")

            if alloc:
                ws2.cell(row=row, column=12, value=alloc.category.name if alloc.category else "")
                ws2.cell(row=row, column=13, value=alloc.sub_category.name if alloc.sub_category else "")
                ws2.cell(row=row, column=14, value=alloc.subdivision.name if alloc.subdivision else "")
                ws2.cell(row=row, column=15, value=alloc.percentage)
            else:
                ws2.cell(row=row, column=12, value="UNALLOCATED")

            ws2.cell(row=row, column=16, value=aging_days if inv.payment_status != "paid" else 0)
            row += 1

    for i in range(1, len(inv_headers) + 1):
        ws2.column_dimensions[get_column_letter(i)].width = 18

    # ── Sheet 3: Payments Ledger ─────────────────────────────────────────────
    ws3 = wb.create_sheet("Payments Ledger")
    pmt_headers = ["Payment Date", "Invoice #", "Vendor", "Billed To", "Amount", "Method", "Reference", "Notes"]
    for i, h in enumerate(pmt_headers, 1):
        c = ws3.cell(row=1, column=i, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")

    payments = (
        db.query(Payment)
        .join(Invoice)
        .filter(Invoice.user_id == current_user.id)
        .order_by(Payment.payment_date.desc())
        .all()
    )
    row = 2
    for pmt in payments:
        inv = db.query(Invoice).filter(Invoice.id == pmt.invoice_id).first()
        if entity and inv and inv.billed_to and entity.lower() not in inv.billed_to.lower():
            continue
        ws3.cell(row=row, column=1, value=pmt.payment_date)
        ws3.cell(row=row, column=2, value=inv.invoice_number if inv else "")
        ws3.cell(row=row, column=3, value=inv.vendor_name if inv else "")
        ws3.cell(row=row, column=4, value=inv.billed_to if inv else "")
        ws3.cell(row=row, column=5, value=round(pmt.amount, 2))
        ws3.cell(row=row, column=6, value=pmt.method)
        ws3.cell(row=row, column=7, value=pmt.reference)
        ws3.cell(row=row, column=8, value=pmt.notes)
        row += 1
    for i in range(1, len(pmt_headers) + 1):
        ws3.column_dimensions[get_column_letter(i)].width = 18

    # ── Sheet 4: Aging Report ────────────────────────────────────────────────
    ws4 = wb.create_sheet("Aging Report")
    aging_headers = ["Invoice #", "Vendor", "Billed To", "Invoice Date", "Due Date", "Total", "Paid", "Balance", "Days Overdue", "Bucket"]
    for i, h in enumerate(aging_headers, 1):
        c = ws4.cell(row=1, column=i, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")

    unpaid_invoices = db.query(Invoice).filter(
        Invoice.user_id == current_user.id,
        Invoice.status == "processed",
        Invoice.payment_status != "paid",
    ).order_by(Invoice.due_date).all()

    row = 2
    for inv in unpaid_invoices:
        if entity and inv.billed_to and entity.lower() not in inv.billed_to.lower():
            continue
        due = inv.due_date or inv.invoice_date
        try:
            days = (datetime.strptime(today_str, "%Y-%m-%d") - datetime.strptime(due, "%Y-%m-%d")).days if due else 0
        except ValueError:
            days = 0
        bucket = "Current" if days <= 30 else "31-60" if days <= 60 else "61-90" if days <= 90 else "90+"
        balance = (inv.total_due or 0) - (inv.amount_paid or 0)

        ws4.cell(row=row, column=1, value=inv.invoice_number)
        ws4.cell(row=row, column=2, value=inv.vendor_name)
        ws4.cell(row=row, column=3, value=inv.billed_to)
        ws4.cell(row=row, column=4, value=inv.invoice_date)
        ws4.cell(row=row, column=5, value=inv.due_date)
        ws4.cell(row=row, column=6, value=round(inv.total_due or 0, 2))
        ws4.cell(row=row, column=7, value=round(inv.amount_paid or 0, 2))
        ws4.cell(row=row, column=8, value=round(balance, 2))
        ws4.cell(row=row, column=9, value=days)
        ws4.cell(row=row, column=10, value=bucket)
        row += 1
    for i in range(1, len(aging_headers) + 1):
        ws4.column_dimensions[get_column_letter(i)].width = 18

    # ── Sheet 5: Entity Summary ──────────────────────────────────────────────
    ws5 = wb.create_sheet("Entity Summary")
    ent_headers = ["Entity (Billed To)", "# Invoices", "Total Invoiced", "Total Paid", "Outstanding", "Billing Type"]
    for i, h in enumerate(ent_headers, 1):
        c = ws5.cell(row=1, column=i, value=h)
        c.font = header_font; c.fill = header_fill; c.alignment = Alignment(horizontal="center")

    # Group by billed_to
    all_inv = db.query(Invoice).filter(
        Invoice.user_id == current_user.id, Invoice.status == "processed"
    ).all()
    entity_map = {}
    for inv in all_inv:
        ent = inv.billed_to or "Unknown"
        if ent not in entity_map:
            entity_map[ent] = {"count": 0, "invoiced": 0.0, "paid": 0.0, "billing_type": set()}
        entity_map[ent]["count"] += 1
        entity_map[ent]["invoiced"] += (inv.total_due or 0)
        entity_map[ent]["paid"] += (inv.amount_paid or 0)
        if inv.billing_type:
            entity_map[ent]["billing_type"].add(inv.billing_type)

    row = 2
    for ent_name, data in sorted(entity_map.items()):
        ws5.cell(row=row, column=1, value=ent_name)
        ws5.cell(row=row, column=2, value=data["count"])
        ws5.cell(row=row, column=3, value=round(data["invoiced"], 2))
        ws5.cell(row=row, column=4, value=round(data["paid"], 2))
        ws5.cell(row=row, column=5, value=round(data["invoiced"] - data["paid"], 2))
        ws5.cell(row=row, column=6, value=", ".join(data["billing_type"]) if data["billing_type"] else "")
        row += 1
    for i in range(1, len(ent_headers) + 1):
        ws5.column_dimensions[get_column_letter(i)].width = 22

    buf = io.BytesIO()
    wb.save(buf)
    buf.seek(0)

    filename = f"bookkeeping_{proj.name.replace(' ', '_')}_{today_str}.xlsx"
    return StreamingResponse(
        buf,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )
