"""
Seed the demo account with a realistic residential construction project.

Run once (or re-run to reset):
  doppler run -- python create_demo.py

Requires DEMO_ENABLED=true in env. Creates user 'demo' with pre-populated:
  - Project: Oakmere Residential Development
  - 4 subdivisions (Phase A–D)
  - 12 cost categories with sub-categories
  - 3 draws (approved / approved / submitted)
  - 2 claims (provincial approved / federal submitted)
  - 20 realistic invoices with Canadian vendors, HST, lender/govt statuses
  - InvoiceAllocation entries linking invoices to categories
"""
import os, sys
from dotenv import load_dotenv
load_dotenv()

if os.getenv("DEMO_ENABLED", "false").strip().lower() not in ("1", "true", "yes"):
    print("ERROR: DEMO_ENABLED is not set to true. Set it in Doppler or .env first.")
    sys.exit(1)

from datetime import datetime
from passlib.context import CryptContext
from app.database import SessionLocal, engine, Base
from app.models import (
    User, Invoice, CategoryConfig, Project, SubDivision,
    CostCategory, CostSubCategory, InvoiceAllocation, Draw, Claim,
)
from app.seed_columns import patch_existing_user_columns

Base.metadata.create_all(bind=engine)
db = SessionLocal()
pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ── 1. Demo user ──────────────────────────────────────────────────────────────
existing = db.query(User).filter(User.username == "demo").first()
if existing:
    print("Resetting demo data (user already exists — clearing invoices, project, categories)…")
    # Clear all data owned by demo user
    for inv in db.query(Invoice).filter(Invoice.user_id == existing.id).all():
        db.delete(inv)
    for cat in db.query(CategoryConfig).filter(CategoryConfig.user_id == existing.id).all():
        db.delete(cat)
    for proj in db.query(Project).filter(Project.user_id == existing.id).all():
        db.delete(proj)
    db.commit()
    demo_user = existing
else:
    demo_user = User(
        username="demo",
        email="demo@finel.ai",
        hashed_password=pwd.hash("demo-preview-2026"),
        is_active=True,
        is_admin=False,
        is_demo=True,
    )
    db.add(demo_user)
    db.commit()
    db.refresh(demo_user)
    print(f"Created demo user id={demo_user.id}")

uid = demo_user.id

# ── 2. Column config (standard fields) ────────────────────────────────────────
patch_existing_user_columns(db, uid)

# ── 3. Category tags (for the Categories view) ────────────────────────────────
cat_tags = [
    ("Site Preparation", 10), ("Foundation & Concrete", 20),
    ("Structural Framing", 30), ("Electrical", 40), ("Plumbing", 50),
    ("HVAC", 60), ("Roofing", 70), ("Windows & Doors", 80),
    ("Insulation", 90), ("Drywall & Finishing", 100),
    ("Flooring", 110), ("Millwork & Cabinetry", 120),
]
saved_tags = {}
for name, order in cat_tags:
    tag = CategoryConfig(user_id=uid, level="category", name=name, display_order=order)
    db.add(tag)
    db.flush()
    saved_tags[name] = tag.id
db.commit()

# ── 4. Project ────────────────────────────────────────────────────────────────
proj = Project(
    user_id=uid,
    name="Oakmere Residential Development",
    code="ORD-2024",
    client="Oakmere Homes Inc.",
    address="1221 Pine Valley Dr, Vaughan, ON L4H 3T6",
    start_date="2024-03-01",
    end_date="2025-08-31",
    total_budget=2_100_000.0,
    currency="CAD",
)
db.add(proj)
db.flush()

# ── 5. Sub-divisions ──────────────────────────────────────────────────────────
phases = {}
for i, (name, desc) in enumerate([
    ("Phase A", "Units 1–3 (South block)"),
    ("Phase B", "Units 4–6 (North block)"),
    ("Phase C", "Units 7–9 (East block)"),
    ("Phase D", "Units 10–12 (West block)"),
], start=1):
    sd = SubDivision(project_id=proj.id, name=name, description=desc, display_order=i * 10)
    db.add(sd)
    db.flush()
    phases[name] = sd.id

# ── 6. Cost categories + sub-categories ───────────────────────────────────────
cost_cats = {}
cat_defs = [
    ("Site Preparation",       95_000,  False, [("Demolition & Clearing", None), ("Grading & Drainage", None), ("Temporary Facilities", None)]),
    ("Foundation & Concrete",  340_000, False, [("Footings", None), ("Foundation Walls", None), ("Slab on Grade", None), ("Waterproofing", None)]),
    ("Structural Framing",     420_000, False, [("Wood Frame", None), ("Steel Beam & Columns", None), ("Sheathing & Wrap", None)]),
    ("Electrical",             205_000, False, [("Rough-in Wiring", None), ("Service Panel & Meter", None), ("Fixtures & Trim", None)]),
    ("Plumbing",               155_000, False, [("Rough-in", None), ("Fixtures & Trim", None), ("Water Service", None)]),
    ("HVAC",                   178_000, False, [("Equipment Supply", None), ("Ductwork & Venting", None), ("Commissioning", None)]),
    ("Roofing",                92_000,  False, [("Shingles & Underlayment", None), ("Flashing & Eavestroughs", None)]),
    ("Windows & Doors",        125_000, False, [("Windows Supply & Install", None), ("Exterior Doors", None), ("Interior Doors", None)]),
    ("Insulation",             58_000,  False, [("Batt Insulation", None), ("Spray Foam", None)]),
    ("Drywall & Finishing",    165_000, False, [("Drywall Supply", None), ("Taping & Mudding", None), ("Painting", None)]),
    ("Flooring",               110_000, False, [("Hardwood", None), ("Tile", None), ("Carpet", None)]),
    ("Millwork & Cabinetry",   157_000, False, [("Kitchen Cabinets", None), ("Bathroom Vanities", None), ("Trim & Moulding", None)]),
]
for order, (name, budget, per_sub, subcats) in enumerate(cat_defs, start=1):
    cc = CostCategory(project_id=proj.id, name=name, budget=budget,
                      is_per_subdivision=per_sub, display_order=order * 10)
    db.add(cc)
    db.flush()
    cost_cats[name] = cc.id
    for so, (sname, sdesc) in enumerate(subcats, start=1):
        db.add(CostSubCategory(category_id=cc.id, name=sname, description=sdesc, display_order=so * 10))

db.commit()

# ── 7. Draws ──────────────────────────────────────────────────────────────────
draw1 = Draw(project_id=proj.id, draw_number=1, status="approved",
             submission_date="2024-06-15", fx_rate=1.0,
             notes="Foundation and sitework complete. Lender inspector sign-off received.")
draw2 = Draw(project_id=proj.id, draw_number=2, status="approved",
             submission_date="2024-09-20", fx_rate=1.0,
             notes="Framing, roofing, and rough MEP complete.")
draw3 = Draw(project_id=proj.id, draw_number=3, status="submitted",
             submission_date="2024-12-05", fx_rate=1.0,
             notes="Windows, insulation, and drywall in progress.")
db.add_all([draw1, draw2, draw3])
db.flush()

# ── 8. Claims ─────────────────────────────────────────────────────────────────
prov_claim = Claim(project_id=proj.id, claim_number=1, claim_type="provincial",
                   status="approved", submission_date="2024-07-10",
                   notes="OHIP infrastructure credit — Phase A.")
fed_claim  = Claim(project_id=proj.id, claim_number=1, claim_type="federal",
                   status="submitted", submission_date="2024-10-15",
                   notes="Federal housing accelerator grant — Phases A+B.")
db.add_all([prov_claim, fed_claim])
db.commit()

# ── 9. Invoices ───────────────────────────────────────────────────────────────
def inv(vendor, num, date, sub, tax, draw, prov=None, fed=None, lender_status="approved",
        govt_status="approved", pay_status="paid", cat_name=None):
    subtotal = round(sub, 2)
    tax_amt  = round(sub * tax, 2)
    total    = round(subtotal + tax_amt, 2)
    l_sub    = round(subtotal * 1.0, 2)
    l_app    = round(l_sub * (0.97 if lender_status == "partial" else 1.0), 2) if lender_status != "pending" else None
    g_sub    = round(subtotal, 2)
    g_app    = round(g_sub * 0.95, 2) if govt_status not in ("pending", "submitted") else None
    return Invoice(
        user_id=uid,
        source="upload",
        original_filename=f"{vendor.lower().replace(' ','_').replace('.','').replace(',','')}_{num}.pdf",
        status="processed",
        confidence_score=0.97,
        invoice_number=num,
        invoice_date=date,
        vendor_name=vendor,
        currency="CAD",
        subtotal=subtotal,
        tax_hst=tax_amt if tax == 0.13 else None,
        tax_gst=tax_amt if tax == 0.05 else None,
        tax_total=tax_amt,
        total_due=total,
        received_total=total,
        vendor_province="ON",
        draw_id=draw,
        provincial_claim_id=prov,
        federal_claim_id=fed,
        lender_submitted_amt=l_sub,
        lender_approved_amt=l_app,
        lender_status=lender_status,
        lender_tax_amt=round(l_sub * 0.13, 2),
        govt_submitted_amt=g_sub,
        govt_approved_amt=g_app,
        govt_status=govt_status,
        payment_status=pay_status,
        amount_paid=total if pay_status == "paid" else (round(total * 0.5, 2) if pay_status == "partially_paid" else 0.0),
        extracted_data={"vendor_name": vendor, "invoice_number": num, "invoice_date": date,
                        "total_due": total, "currency": "CAD"},
        processed_at=datetime(2024, int(date[5:7]), int(date[8:10])),
    )

D1, D2, D3 = draw1.id, draw2.id, draw3.id
P1, F1 = prov_claim.id, fed_claim.id

invoices = [
  # Draw 1 — Foundation & Sitework
  inv("GreenBuild Excavation Inc.",   "GB-1041",   "2024-04-18", 42_800,  0.13, D1, P1,   None, cat_name="Site Preparation"),
  inv("Maple Concrete Ltd.",          "MCL-2240",  "2024-04-29", 68_500,  0.13, D1, P1,   None, cat_name="Foundation & Concrete"),
  inv("Ridgeway Building Supplies",   "RBS-0887",  "2024-05-10", 21_300,  0.13, D1, P1,   None, cat_name="Foundation & Concrete"),
  inv("Ontario Rebar Supply Co.",     "ORS-3312",  "2024-05-22", 14_600,  0.13, D1, P1,   None, "approved", "approved", "paid",      cat_name="Foundation & Concrete"),
  inv("EllisDon Site Services",       "EDS-7750",  "2024-06-02", 31_200,  0.13, D1, P1,   None, cat_name="Site Preparation"),
  # Draw 2 — Framing, Roofing, MEP rough-in
  inv("Structurlam Mass Timber",      "SLM-4418",  "2024-07-08", 88_400,  0.13, D2, P1,   F1,  cat_name="Structural Framing"),
  inv("Atlas Roofing Corp.",          "ARC-6621",  "2024-07-25", 37_900,  0.13, D2, None, F1,  cat_name="Roofing"),
  inv("Ontario Electrical Services",  "OES-1129",  "2024-08-05", 52_100,  0.13, D2, None, F1,  cat_name="Electrical"),
  inv("Mueller Industries Canada",    "MIC-8843",  "2024-08-14", 18_750,  0.13, D2, None, F1,  cat_name="Plumbing"),
  inv("Lennox Intl — HVAC Dist.",     "LID-3307",  "2024-08-28", 61_400,  0.13, D2, None, F1,  "partial", "submitted", "paid",      cat_name="HVAC"),
  inv("Pella Windows & Doors ON",     "PWD-2251",  "2024-09-10", 43_800,  0.13, D2, None, F1,  cat_name="Windows & Doors"),
  inv("Ideal Supply Co.",             "ISC-9945",  "2024-09-18", 11_200,  0.13, D2, None, F1,  "approved", "submitted", "paid",      cat_name="Electrical"),
  # Draw 3 — Finishes in progress
  inv("USG Canada Ltd.",              "USG-7732",  "2024-10-05", 29_600,  0.13, D3, None, None, "pending", "pending", "unpaid", "Drywall & Finishing"),
  inv("Atlas Insulation Solutions",   "AIS-0341",  "2024-10-17", 16_900,  0.13, D3, None, None, "pending", "pending", "unpaid", "Insulation"),
  inv("Armstrong Flooring Canada",    "AFC-5519",  "2024-11-01", 34_200,  0.13, D3, None, None, "pending", "pending", "partially_paid", "Flooring"),
  inv("Sherwin-Williams Pro",         "SWP-2281",  "2024-11-12", 8_400,   0.13, D3, None, None, "pending", "pending", "unpaid", "Drywall & Finishing"),
  inv("Woodland Millwork & Cabinet",  "WMC-6630",  "2024-11-20", 58_700,  0.13, D3, None, None, "pending", "pending", "unpaid", "Millwork & Cabinetry"),
  inv("Carrier Canada HVAC",          "CCA-4472",  "2024-11-28", 22_300,  0.13, D3, None, None, "pending", "pending", "unpaid", "HVAC"),
  inv("Home Depot Pro Supply",        "HDP-1190",  "2024-12-02", 7_850,   0.13, D3, None, None, "pending", "pending", "unpaid", "Drywall & Finishing"),
  inv("Simpson Strong-Tie Canada",    "SST-3381",  "2024-12-04", 5_620,   0.05, D3, None, None, "pending", "pending", "unpaid", "Structural Framing"),
]

for i in invoices:
    db.add(i)
db.flush()

# ── 10. InvoiceAllocations (link Draw 1+2 invoices to cost categories) ─────────
alloc_map = [
    (invoices[0],  "Site Preparation",      None),
    (invoices[1],  "Foundation & Concrete", "Foundation Walls"),
    (invoices[2],  "Foundation & Concrete", "Slab on Grade"),
    (invoices[3],  "Foundation & Concrete", "Footings"),
    (invoices[4],  "Site Preparation",      "Grading & Drainage"),
    (invoices[5],  "Structural Framing",    "Wood Frame"),
    (invoices[6],  "Roofing",               "Shingles & Underlayment"),
    (invoices[7],  "Electrical",            "Rough-in Wiring"),
    (invoices[8],  "Plumbing",              "Rough-in"),
    (invoices[9],  "HVAC",                  "Equipment Supply"),
    (invoices[10], "Windows & Doors",       "Windows Supply & Install"),
    (invoices[11], "Electrical",            "Service Panel & Meter"),
]
for inv_obj, cat_name, subcat_name in alloc_map:
    cat_id = cost_cats.get(cat_name)
    if not cat_id:
        continue
    # find subcat
    sub_id = None
    if subcat_name:
        sc = db.query(CostSubCategory).filter(
            CostSubCategory.category_id == cat_id,
            CostSubCategory.name == subcat_name,
        ).first()
        if sc:
            sub_id = sc.id
    alloc = InvoiceAllocation(
        invoice_id=inv_obj.id,
        category_id=cat_id,
        sub_category_id=sub_id,
        subdivision_id=phases.get("Phase A"),
        percentage=100.0,
        amount=inv_obj.total_due,
    )
    db.add(alloc)

total_inv = len(invoices)
total_val = sum(i.total_due for i in invoices)
db.commit()
db.close()
print(f"\nDemo seeded successfully.")
print(f"  User:      demo / demo-preview-2026")
print(f"  Project:   Oakmere Residential Development (budget $2,100,000)")
print(f"  Invoices:  {total_inv} invoices, ${total_val:,.2f} total")
print(f"  Draws:     3 (1 approved, 1 approved, 1 submitted)")
print(f"  Claims:    1 provincial (approved), 1 federal (submitted)")
print(f"  Endpoint:  POST /api/auth/demo")
