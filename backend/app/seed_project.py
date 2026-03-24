"""Seed default project, sub-divisions, cost categories, and sub-categories."""
from sqlalchemy.orm import Session
from .models import Project, SubDivision, CostCategory, CostSubCategory


def seed_project_finance(db: Session, user_id: int):
    """Create the default project structure if it doesn't exist yet."""
    existing = db.query(Project).filter(Project.user_id == user_id).first()
    if existing:
        return  # Already seeded

    # ── Project ──────────────────────────────────────────────────────────────
    proj = Project(
        user_id=user_id,
        name="FTTH Network Build",
        currency="CAD",
    )
    db.add(proj)
    db.flush()  # get proj.id

    # ── Sub-Divisions ────────────────────────────────────────────────────────
    for i in range(1, 6):
        db.add(SubDivision(project_id=proj.id, name=str(i), display_order=i * 10))

    # ── Cost Categories + Sub-Categories ─────────────────────────────────────

    # 1. Payroll
    db.add(CostCategory(project_id=proj.id, name="Payroll", display_order=10))

    # 2. Material
    mat = CostCategory(project_id=proj.id, name="Material", display_order=20)
    db.add(mat)
    db.flush()
    for order, (name, desc) in enumerate([
        ("Vaults and Handholes", "Vaults, Handholes, Flower Pots, Splicing (from 144-strand to spur lines)"),
        ("Fibre and Cable Infrastructure", "Fibre Cable, Conduit, Strand, Mule Tape"),
        ("Splicing & Terminations", "Splice Closures, Splitters, Connectors, FOSC, Patch Panels, Patch Cables, Pigtailed Cassettes"),
        ("Distribution & Access Devices", "Port Terminals, NID, POP Terminations"),
        ("Misc.", None),
    ], start=1):
        db.add(CostSubCategory(category_id=mat.id, name=name, description=desc, display_order=order * 10))

    # 3. Electronics
    elec = CostCategory(project_id=proj.id, name="Electronics", display_order=30)
    db.add(elec)
    db.flush()
    for order, (name, desc) in enumerate([
        ("OLT & Chassis Kits", "7360 OLT Chassis Kits, Chassis (7750 SR Hardware)"),
        ("ONTs & Optical Modules", "ONTs (GPON/XGS), Line Cards, Optical Modules"),
        ("PSS & Transponders", "PSS8 Kits, Filters, Cables, Transponders, Uplink, Spares"),
        ("Network Software & Tools", "Element Management Software, Network Management (NSP, NFM-T)"),
        ("Professional Services & Training", "Architecture Design, IP Routing Design, Optical Integration, Training (FBA, IPR)"),
    ], start=1):
        db.add(CostSubCategory(category_id=elec.id, name=name, description=desc, display_order=order * 10))

    # 4. Make Ready
    db.add(CostCategory(project_id=proj.id, name="Make Ready", display_order=40))

    # 5. Fiber Build (per sub-division)
    fb = CostCategory(project_id=proj.id, name="Fiber Build", is_per_subdivision=True, display_order=50)
    db.add(fb)
    db.flush()
    for order, name in enumerate([
        "Mobilization",
        "Drawings / Design and Engineering",
        "Aerial Installation",
        "Underground Installation",
        "Drops",
        "Construction Support",
    ], start=1):
        db.add(CostSubCategory(category_id=fb.id, name=name, display_order=order * 10))

    db.commit()
