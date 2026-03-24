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
)
from ..schemas import (
    ProjectCreate, ProjectUpdate, ProjectOut,
    SubDivisionOut, CostCategoryOut, CostCategoryCreate, CostCategoryUpdate,
    CostSubCategoryCreate, CostSubCategoryOut,
    SubDivisionBudgetSet, AllocationCreate, AllocationOut,
    PaymentCreate, PaymentOut,
)
from ..dependencies import get_current_user

router = APIRouter(prefix="/api/project", tags=["project"])


# ─── Project CRUD ────────────────────────────────────────────────────────────

@router.get("", response_model=Optional[ProjectOut])
def get_project(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    """Get the user's project (single-project model)."""
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    return proj


@router.post("", response_model=ProjectOut)
def create_project(body: ProjectCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    existing = db.query(Project).filter(Project.user_id == current_user.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Project already exists. Use PUT to update.")
    proj = Project(user_id=current_user.id, **body.model_dump())
    db.add(proj)
    db.commit()
    db.refresh(proj)
    return proj


@router.put("", response_model=ProjectOut)
def update_project(body: ProjectUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="No project found")
    _ALLOWED = {"name", "code", "client", "address", "start_date", "end_date", "total_budget", "currency"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in _ALLOWED:
            setattr(proj, field, value)
    db.commit()
    db.refresh(proj)
    return proj


# ─── Sub-Divisions ───────────────────────────────────────────────────────────

@router.get("/subdivisions", response_model=List[SubDivisionOut])
def list_subdivisions(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        return []
    return db.query(SubDivision).filter(SubDivision.project_id == proj.id).order_by(SubDivision.display_order).all()


@router.post("/subdivisions", response_model=SubDivisionOut)
def create_subdivision(name: str, description: str = None, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Create a project first")
    sd = SubDivision(project_id=proj.id, name=name, description=description)
    db.add(sd)
    db.commit()
    db.refresh(sd)
    return sd


# ─── Cost Categories ─────────────────────────────────────────────────────────

@router.get("/categories", response_model=List[CostCategoryOut])
def list_cost_categories(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        return []
    return (
        db.query(CostCategory)
        .filter(CostCategory.project_id == proj.id)
        .order_by(CostCategory.display_order)
        .all()
    )


@router.post("/categories", response_model=CostCategoryOut)
def create_cost_category(body: CostCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Create a project first")
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
def update_cost_category(cat_id: int, body: CostCategoryUpdate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404)
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    _ALLOWED = {"name", "budget"}
    for field, value in body.model_dump(exclude_unset=True).items():
        if field in _ALLOWED:
            setattr(cat, field, value)
    db.commit()
    db.refresh(cat)
    return cat


@router.delete("/categories/{cat_id}")
def delete_cost_category(cat_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404)
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    db.delete(cat)
    db.commit()
    return {"message": "Deleted"}


# ─── Cost Sub-Categories ─────────────────────────────────────────────────────

@router.post("/categories/{cat_id}/subcategories", response_model=CostSubCategoryOut)
def create_cost_subcategory(cat_id: int, body: CostSubCategoryCreate, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404)
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
    if not cat:
        raise HTTPException(status_code=404, detail="Cost category not found")
    sc = CostSubCategory(category_id=cat_id, name=body.name, description=body.description, budget=body.budget)
    db.add(sc)
    db.commit()
    db.refresh(sc)
    return sc


@router.delete("/subcategories/{sc_id}")
def delete_cost_subcategory(sc_id: int, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404)
    sc = db.query(CostSubCategory).join(CostCategory).filter(
        CostSubCategory.id == sc_id, CostCategory.project_id == proj.id
    ).first()
    if not sc:
        raise HTTPException(status_code=404)
    db.delete(sc)
    db.commit()
    return {"message": "Deleted"}


# ─── Sub-Division Budgets (for Fiber Build etc.) ─────────────────────────────

@router.put("/categories/{cat_id}/subdivision-budgets")
def set_subdivision_budgets(cat_id: int, budgets: List[SubDivisionBudgetSet], db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404)
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
    if not cat:
        raise HTTPException(status_code=404)
    # Upsert budgets
    for b in budgets:
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
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        return []
    # Verify category belongs to user's project
    cat = db.query(CostCategory).filter(CostCategory.id == cat_id, CostCategory.project_id == proj.id).first()
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
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Create a project first")

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


# ─── Dashboard ────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def project_dashboard(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
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

        cat_data = {
            "id": cat.id,
            "name": cat.name,
            "budget": cat.budget,
            "invoiced": round(alloc_sum, 2),
            "paid": round(paid_sum, 2),
            "remaining": round(cat.budget - alloc_sum, 2),
            "is_per_subdivision": cat.is_per_subdivision,
            "sub_categories": [{"id": sc.id, "name": sc.name, "budget": sc.budget} for sc in cat.sub_categories],
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

    return {
        "project": ProjectOut.model_validate(proj).model_dump(),
        "total_budget": total_budget,
        "total_invoiced": round(total_invoiced, 2),
        "total_paid": round(total_paid, 2),
        "total_remaining": round(total_budget - total_invoiced, 2),
        "categories": cat_summary,
        "unallocated_invoices": unallocated,
        "aging": {k: round(v, 2) for k, v in aging.items()},
    }


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

    proj = db.query(Project).filter(Project.user_id == current_user.id).first()
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
