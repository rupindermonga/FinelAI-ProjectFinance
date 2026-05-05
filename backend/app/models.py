from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, Float, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    is_demo = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoices = relationship("Invoice", back_populates="user", cascade="all, delete-orphan")
    column_configs = relationship("ColumnConfig", back_populates="user", cascade="all, delete-orphan")
    category_configs = relationship("CategoryConfig", back_populates="user", cascade="all, delete-orphan")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # Source tracking
    source = Column(String, default="upload")  # upload | email | folder
    source_file = Column(String, nullable=True)
    source_email = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)

    # Processing metadata
    processed_at = Column(DateTime, default=datetime.utcnow)
    status = Column(String, default="pending")  # pending | processing | processed | error
    error_message = Column(Text, nullable=True)
    confidence_score = Column(Float, nullable=True)

    # Key indexed fields for fast filtering
    invoice_number = Column(String, nullable=True, index=True)
    invoice_date = Column(String, nullable=True, index=True)
    due_date = Column(String, nullable=True)
    vendor_name = Column(String, nullable=True, index=True)
    currency = Column(String, nullable=True, index=True)
    total_due = Column(Float, nullable=True)

    # All extracted data as JSON (flexible, driven by column config)
    extracted_data = Column(JSON, nullable=True)

    # Entity / billing tracking
    billed_to = Column(String, nullable=True, index=True)       # entity that received the invoice
    billing_type = Column(String, nullable=True)                 # direct | pass_through
    vendor_on_record = Column(String, nullable=True)             # subsidiary acting as intermediary

    # Tax breakdown (extracted by Gemini)
    subtotal = Column(Float, nullable=True)              # before tax
    tax_gst = Column(Float, nullable=True)               # 5% federal GST
    tax_hst = Column(Float, nullable=True)               # 13% Ontario HST (includes GST)
    tax_qst = Column(Float, nullable=True)               # 9.975% Quebec QST
    tax_pst = Column(Float, nullable=True)               # provincial sales tax (BC, SK, MB)
    tax_total = Column(Float, nullable=True)             # total tax on invoice
    vendor_province = Column(String, nullable=True)      # province/state of vendor

    # Cost tracking — what we received vs what we bill
    received_total = Column(Float, nullable=True)        # = total_due (what vendor billed us)

    # Lender billing
    lender_margin_pct = Column(Float, default=0.0)       # margin % for lender (0 going forward)
    lender_margin_amt = Column(Float, default=0.0)       # computed: subtotal * margin_pct / 100
    lender_submitted_amt = Column(Float, nullable=True)  # subtotal + margin + recalculated tax
    lender_approved_amt = Column(Float, nullable=True)   # what lender approved (may differ)
    lender_status = Column(String, default="pending")    # pending | approved | partial | rejected
    lender_tax_amt = Column(Float, nullable=True)        # recalculated tax (HST or QST+GST based on VoR)

    # Govt billing (same amounts for both provincial and federal)
    govt_margin_pct = Column(Float, default=0.0)         # margin % for govt (0 going forward)
    govt_margin_amt = Column(Float, default=0.0)         # computed: subtotal * margin_pct / 100
    govt_submitted_amt = Column(Float, nullable=True)    # subtotal + margin (no tax claimable)
    govt_approved_amt = Column(Float, nullable=True)     # what govt approved
    govt_status = Column(String, default="pending")      # pending | approved | partial | rejected

    # Payment tracking
    payment_status = Column(String, default="unpaid")  # unpaid | partially_paid | paid
    amount_paid = Column(Float, default=0.0)

    # Project linking (direct — for filtering invoices by project without going through draws)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=True, index=True)

    # Draw / Claim linking
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)
    provincial_claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True)
    federal_claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True)

    # Holdback / retainage (Ontario Construction Act — typically 10%)
    holdback_pct = Column(Float, default=10.0)         # % withheld (0 = no holdback)
    holdback_released = Column(Boolean, default=False)
    holdback_released_date = Column(String, nullable=True)   # YYYY-MM-DD

    # Invoice approval workflow
    approval_status = Column(String, default="pending")  # pending | approved | rejected
    approved_by = Column(String, nullable=True)           # username of approver
    approved_at = Column(String, nullable=True)           # YYYY-MM-DD

    # Payroll flag
    is_payroll = Column(Boolean, default=False)

    user = relationship("User", back_populates="invoices")
    draw = relationship("Draw", foreign_keys=[draw_id], back_populates="invoices")
    provincial_claim = relationship("Claim", foreign_keys=[provincial_claim_id], back_populates="provincial_invoices")
    federal_claim = relationship("Claim", foreign_keys=[federal_claim_id], back_populates="federal_invoices")
    allocations = relationship("InvoiceAllocation", back_populates="invoice", cascade="all, delete-orphan")
    payments = relationship("Payment", back_populates="invoice", cascade="all, delete-orphan")


class ColumnConfig(Base):
    __tablename__ = "column_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    field_key = Column(String, nullable=False)        # e.g. "vendor_name"
    field_label = Column(String, nullable=False)      # e.g. "Vendor Name"
    field_description = Column(String, nullable=True) # used in Gemini prompt
    field_type = Column(String, default="string")     # string | number | date | array | boolean
    is_active = Column(Boolean, default=True)         # extracted by Gemini
    is_viewable = Column(Boolean, default=True)       # shown in dashboard table
    is_system = Column(Boolean, default=False)        # cannot be deleted, only toggled
    is_exportable = Column(Boolean, default=True)     # included in Excel/JSON export
    display_order = Column(Integer, default=100)

    user = relationship("User", back_populates="column_configs")


class CategoryConfig(Base):
    __tablename__ = "category_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # level: "category" | "sub_category" | "sub_division"
    level = Column(String, nullable=False)
    name = Column(String, nullable=False)

    # parent_id: null for top-level categories,
    #            category id for sub_categories,
    #            sub_category id for sub_divisions
    parent_id = Column(Integer, ForeignKey("category_configs.id"), nullable=True)

    is_active = Column(Boolean, default=True)
    display_order = Column(Integer, default=100)
    # Only meaningful for level="category": if True, Gemini uses "Not Available"
    # when sub-division is applicable but not found; if False, leaves it blank
    requires_sub_division = Column(Boolean, default=False)

    user = relationship("User", back_populates="category_configs")
    parent = relationship("CategoryConfig", remote_side=[id], back_populates="children")
    children = relationship("CategoryConfig", back_populates="parent", cascade="all, delete-orphan")


class Correction(Base):
    """Stores user corrections to extracted data — used as few-shot examples in future prompts."""
    __tablename__ = "corrections"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    field_key = Column(String, nullable=False)        # e.g. "category"
    original_value = Column(String, nullable=True)     # what Gemini returned
    corrected_value = Column(String, nullable=False)   # what the user chose
    vendor_name = Column(String, nullable=True)        # context: which vendor
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


# ─── Project Finance Models ──────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    client = Column(String, nullable=True)
    address = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    total_budget = Column(Float, default=0.0)
    currency = Column(String, default="CAD")
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    sub_divisions = relationship("SubDivision", back_populates="project", cascade="all, delete-orphan")
    cost_categories = relationship("CostCategory", back_populates="project", cascade="all, delete-orphan")


class SubDivision(Base):
    __tablename__ = "sub_divisions"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)           # "1", "2", "3", "4", "5"
    description = Column(String, nullable=True)
    display_order = Column(Integer, default=100)

    project = relationship("Project", back_populates="sub_divisions")


class CostCategory(Base):
    """Top-level cost category: Payroll, Material, Electronics, Make Ready, Fiber Build, etc."""
    __tablename__ = "cost_categories"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    name = Column(String, nullable=False)
    budget = Column(Float, default=0.0)              # total budget for this category
    is_per_subdivision = Column(Boolean, default=False)  # True = Fiber Build (budget per sub-division)
    display_order = Column(Integer, default=100)

    project = relationship("Project", back_populates="cost_categories")
    sub_categories = relationship("CostSubCategory", back_populates="category", cascade="all, delete-orphan")
    subdivision_budgets = relationship("SubDivisionBudget", back_populates="category", cascade="all, delete-orphan")


class CostSubCategory(Base):
    """Sub-category within a cost category (e.g. OLT & Chassis under Electronics)."""
    __tablename__ = "cost_sub_categories"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)        # what's included
    budget = Column(Float, nullable=True)             # optional per-sub-category budget
    display_order = Column(Integer, default=100)

    category = relationship("CostCategory", back_populates="sub_categories")


class SubDivisionBudget(Base):
    """Budget allocation per sub-division for categories that split by sub-division (Fiber Build)."""
    __tablename__ = "subdivision_budgets"

    id = Column(Integer, primary_key=True, index=True)
    category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=False)
    subdivision_id = Column(Integer, ForeignKey("sub_divisions.id"), nullable=False)
    budget = Column(Float, default=0.0)

    category = relationship("CostCategory", back_populates="subdivision_budgets")
    subdivision = relationship("SubDivision")


class InvoiceAllocation(Base):
    """Links an invoice to a cost category + optional sub-category + sub-division(s) with % split."""
    __tablename__ = "invoice_allocations"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=False, index=True)
    sub_category_id = Column(Integer, ForeignKey("cost_sub_categories.id"), nullable=True)
    subdivision_id = Column(Integer, ForeignKey("sub_divisions.id"), nullable=True)
    percentage = Column(Float, default=100.0)         # % of invoice allocated here
    amount = Column(Float, default=0.0)               # computed: invoice.total_due * percentage / 100

    invoice = relationship("Invoice", back_populates="allocations")
    category = relationship("CostCategory")
    sub_category = relationship("CostSubCategory")
    subdivision = relationship("SubDivision")


class Payment(Base):
    """Payment record against an invoice."""
    __tablename__ = "payments"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False, index=True)
    amount = Column(Float, nullable=False)
    payment_date = Column(String, nullable=False)     # YYYY-MM-DD
    method = Column(String, nullable=True)            # cheque | etransfer | wire | eft
    reference = Column(String, nullable=True)         # cheque # or transaction ref
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    invoice = relationship("Invoice", back_populates="payments")


class Draw(Base):
    """A draw submission to lenders — groups invoices with a single FX rate."""
    __tablename__ = "draws"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    draw_number = Column(Integer, nullable=False)
    fx_rate = Column(Float, default=1.0)          # USD→CAD rate for this draw
    submission_date = Column(String, nullable=True)
    status = Column(String, default="draft")      # draft | submitted | approved | funded
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    invoices = relationship("Invoice", foreign_keys="Invoice.draw_id", back_populates="draw")


class Claim(Base):
    """A claim submission to government (provincial or federal)."""
    __tablename__ = "claims"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)
    claim_number = Column(Integer, nullable=False)
    claim_type = Column(String, nullable=False)   # provincial | federal
    fx_rate = Column(Float, default=1.0)          # USD→CAD rate for this claim
    submission_date = Column(String, nullable=True)
    status = Column(String, default="draft")      # draft | submitted | approved | received
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    provincial_invoices = relationship("Invoice", foreign_keys="Invoice.provincial_claim_id", back_populates="provincial_claim")
    federal_invoices = relationship("Invoice", foreign_keys="Invoice.federal_claim_id", back_populates="federal_claim")


class PayrollEntry(Base):
    """A payroll record — extracted from paystubs or entered manually."""
    __tablename__ = "payroll_entries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False)

    # Employee / period info
    employee_name = Column(String, nullable=True)
    company_name = Column(String, nullable=True)          # which subsidiary ran the payroll
    pay_period_start = Column(String, nullable=True)      # YYYY-MM-DD
    pay_period_end = Column(String, nullable=True)        # YYYY-MM-DD

    # Amounts
    gross_pay = Column(Float, default=0.0)
    net_pay = Column(Float, nullable=True)
    cpp = Column(Float, default=0.0)                     # Canada Pension Plan
    ei = Column(Float, default=0.0)                      # Employment Insurance
    income_tax = Column(Float, default=0.0)
    insurance = Column(Float, default=0.0)
    holiday_pay = Column(Float, default=0.0)
    other_deductions = Column(Float, default=0.0)

    # Working days calculation
    total_calendar_days = Column(Integer, nullable=True)
    working_days = Column(Integer, nullable=True)         # total working days in period
    statutory_holidays = Column(Integer, default=0)       # holidays to deduct (Ontario/Quebec)
    eligible_days = Column(Integer, nullable=True)        # working_days - statutory_holidays
    daily_rate = Column(Float, nullable=True)             # gross_pay / eligible_days
    province = Column(String, default="ON")               # ON | QC — affects holiday rules

    # Billing
    lender_billable = Column(Float, nullable=True)        # full gross (lender approves all)
    govt_billable = Column(Float, nullable=True)          # gross - (CPP + EI + Insurance + Holiday pay)
    lender_submitted_amt = Column(Float, nullable=True)
    lender_approved_amt = Column(Float, nullable=True)
    lender_status = Column(String, default="pending")
    govt_submitted_amt = Column(Float, nullable=True)
    govt_approved_amt = Column(Float, nullable=True)
    govt_status = Column(String, default="pending")

    # Linking
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)
    provincial_claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True)
    federal_claim_id = Column(Integer, ForeignKey("claims.id"), nullable=True)

    # Source
    source_file = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    status = Column(String, default="pending")           # pending | processing | processed | error
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")
    project = relationship("Project")


class CommittedCost(Base):
    """An approved contract or PO — spend committed but not yet invoiced.
    Closes the gap between budget and invoiced in the budget vs actual view."""
    __tablename__ = "committed_costs"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=True)
    vendor = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    contract_amount = Column(Float, nullable=False)    # total value of the contract
    invoiced_to_date = Column(Float, default=0.0)      # how much has been invoiced so far (auto-computable but manually editable)
    status = Column(String, default="active")          # active | complete | cancelled
    contract_date = Column(String, nullable=True)
    expected_completion = Column(String, nullable=True)
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    category = relationship("CostCategory")


class ChangeOrder(Base):
    """A change order adjusts the approved budget for a cost category (positive = scope increase, negative = reduction)."""
    __tablename__ = "change_orders"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=True)   # None = project-level CO
    co_number = Column(String, nullable=False)        # e.g. "CO-001"
    description = Column(Text, nullable=False)
    amount = Column(Float, nullable=False)            # positive = increase, negative = credit/reduction
    status = Column(String, default="pending")        # pending | approved | rejected
    issued_by = Column(String, nullable=True)         # contractor / trade name
    date = Column(String, nullable=True)              # YYYY-MM-DD
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    category = relationship("CostCategory")


class GeminiApiKey(Base):
    """Admin-managed pool of Gemini API keys — tried in priority order with fallback."""
    __tablename__ = "gemini_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)        # e.g. "Primary Key", "Backup Key 1"
    key_value = Column(String, nullable=False)    # actual API key (admin-only access)
    priority = Column(Integer, default=100)       # lower number = tried first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
