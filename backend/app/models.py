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

    # Payment tracking
    payment_status = Column(String, default="unpaid")  # unpaid | partially_paid | paid
    amount_paid = Column(Float, default=0.0)

    user = relationship("User", back_populates="invoices")
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
    is_active = Column(Boolean, default=True)         # shown in table + extracted
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


class GeminiApiKey(Base):
    """Admin-managed pool of Gemini API keys — tried in priority order with fallback."""
    __tablename__ = "gemini_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)        # e.g. "Primary Key", "Backup Key 1"
    key_value = Column(String, nullable=False)    # actual API key (admin-only access)
    priority = Column(Integer, default=100)       # lower number = tried first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
