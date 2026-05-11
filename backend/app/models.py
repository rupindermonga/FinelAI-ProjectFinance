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
    org_id  = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)

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


# ─── Multi-Tenant: Organization & Members ─────────────────────────────────────

class Organization(Base):
    """A company/tenant. All data is scoped to an org."""
    __tablename__ = "organizations"

    id          = Column(Integer, primary_key=True, index=True)
    name        = Column(String, nullable=False)
    slug        = Column(String, unique=True, nullable=False, index=True)   # url-safe short id
    plan        = Column(String, default="starter")   # starter | pro | enterprise
    is_active   = Column(Boolean, default=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    members     = relationship("OrganizationMember", back_populates="organization",
                               cascade="all, delete-orphan",
                               foreign_keys="OrganizationMember.org_id")
    vendors     = relationship("OrgVendor", back_populates="organization",
                               cascade="all, delete-orphan")


class OrganizationMember(Base):
    """Maps a User to an Organization with a role.

    Roles:
      owner          — full access to Finance + PM, billing, delete org
      admin          — full Finance + PM, no billing/delete  (legacy: admin)
      finance_admin  — full Finance, read-only PM
      pm_admin       — full PM, read-only Finance
      finance_viewer — read-only Finance, no PM
      pm_viewer      — read-only PM, no Finance
      site_supervisor— PM edit (tasks/logs), no Finance
      editor         — full Finance edit (legacy)
      viewer         — read-only Finance (legacy)
      vendor_finance — submit own invoices + view own invoice status only
      vendor_pm      — update assigned tasks + daily logs
    """
    __tablename__ = "organization_members"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    role        = Column(String, default="editor")
    is_active   = Column(Boolean, default=True)
    invited_by  = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="members",
                                foreign_keys=[org_id])
    user         = relationship("User", foreign_keys=[user_id])
    inviter      = relationship("User", foreign_keys=[invited_by])


class PasswordResetToken(Base):
    """Single-use password reset tokens (1-hour TTL)."""
    __tablename__ = "password_reset_tokens"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    token      = Column(String, unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    used       = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User")


class OrgInvitation(Base):
    """Email invitation to join an organisation (7-day TTL)."""
    __tablename__ = "org_invitations"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    email       = Column(String, nullable=False, index=True)
    role        = Column(String, default="editor")
    token       = Column(String, unique=True, nullable=False, index=True)
    invited_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at  = Column(DateTime, nullable=False)
    accepted_at = Column(DateTime, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization")
    inviter      = relationship("User")


# ─── Project Management Models ───────────────────────────────────────────────

class Task(Base):
    """Project Management task / work item."""
    __tablename__ = "pm_tasks"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    parent_id       = Column(Integer, ForeignKey("pm_tasks.id"), nullable=True)
    title           = Column(String, nullable=False)
    description     = Column(Text, nullable=True)
    task_type       = Column(String, default="task")     # task | milestone | issue
    status          = Column(String, default="not_started")  # not_started | in_progress | completed | blocked | cancelled
    priority        = Column(String, default="medium")   # low | medium | high | critical
    assigned_to     = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    start_date      = Column(String, nullable=True)
    end_date        = Column(String, nullable=True)
    due_date        = Column(String, nullable=True)
    percent_complete = Column(Integer, default=0)
    location        = Column(String, nullable=True)      # e.g. "Level 3 - North wing"
    tags            = Column(String, nullable=True)      # comma-separated
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    assignee  = relationship("User", foreign_keys=[assigned_to])
    creator   = relationship("User", foreign_keys=[created_by])
    subtasks  = relationship("Task", backref=__import__('sqlalchemy.orm', fromlist=['backref']).backref("parent", remote_side=[id]))
    comments  = relationship("TaskComment", back_populates="task", cascade="all, delete-orphan")


class TaskComment(Base):
    __tablename__ = "pm_task_comments"

    id         = Column(Integer, primary_key=True, index=True)
    task_id    = Column(Integer, ForeignKey("pm_tasks.id"), nullable=False, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    comment    = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    task = relationship("Task", back_populates="comments")
    user = relationship("User")


class DailyLog(Base):
    """Daily site log / progress report."""
    __tablename__ = "pm_daily_logs"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    log_date    = Column(String, nullable=False, index=True)
    weather     = Column(String, nullable=True)          # sunny | cloudy | rain | snow | wind
    temperature = Column(String, nullable=True)          # e.g. "12°C"
    crew_count  = Column(Integer, default=0)
    work_summary = Column(Text, nullable=True)
    issues      = Column(Text, nullable=True)
    delays      = Column(Text, nullable=True)
    visitors    = Column(Text, nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class RFI(Base):
    """Request for Information."""
    __tablename__ = "pm_rfis"

    id           = Column(Integer, primary_key=True, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    rfi_number   = Column(String, nullable=False)
    subject      = Column(String, nullable=False)
    description  = Column(Text, nullable=True)
    status       = Column(String, default="open")        # open | answered | closed
    priority     = Column(String, default="medium")
    assigned_to  = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date     = Column(String, nullable=True)
    response     = Column(Text, nullable=True)
    responded_by = Column(Integer, ForeignKey("users.id"), nullable=True)
    responded_at = Column(DateTime, nullable=True)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    creator    = relationship("User", foreign_keys=[created_by])
    assignee   = relationship("User", foreign_keys=[assigned_to])
    responder  = relationship("User", foreign_keys=[responded_by])


class PunchItem(Base):
    """Punch list / deficiency item."""
    __tablename__ = "pm_punch_items"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    item_number = Column(String, nullable=False)
    title       = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    location    = Column(String, nullable=True)
    status      = Column(String, default="open")         # open | in_progress | resolved | verified
    priority    = Column(String, default="medium")
    assigned_to = Column(Integer, ForeignKey("users.id"), nullable=True)
    due_date    = Column(String, nullable=True)
    resolved_at = Column(DateTime, nullable=True)
    photo_path  = Column(String, nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator  = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])


class Submittal(Base):
    """Shop drawing / material submittal."""
    __tablename__ = "pm_submittals"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    submittal_number = Column(String, nullable=False)
    title           = Column(String, nullable=False)
    description     = Column(Text, nullable=True)
    spec_section    = Column(String, nullable=True)
    status          = Column(String, default="draft")    # draft | submitted | under_review | approved | rejected | resubmit
    submitted_by    = Column(Integer, ForeignKey("users.id"), nullable=True)
    submitted_date  = Column(String, nullable=True)
    reviewer        = Column(Integer, ForeignKey("users.id"), nullable=True)
    review_date     = Column(String, nullable=True)
    review_notes    = Column(Text, nullable=True)
    file_path       = Column(String, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    creator   = relationship("User", foreign_keys=[created_by])
    submitter = relationship("User", foreign_keys=[submitted_by])
    reviewer_ = relationship("User", foreign_keys=[reviewer])


class MeetingMinutes(Base):
    """Meeting minutes with action items."""
    __tablename__ = "pm_meetings"

    id           = Column(Integer, primary_key=True, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    meeting_date = Column(String, nullable=False, index=True)
    title        = Column(String, nullable=False)
    location     = Column(String, nullable=True)
    attendees    = Column(Text, nullable=True)            # JSON array of names
    agenda       = Column(Text, nullable=True)
    minutes      = Column(Text, nullable=True)
    action_items = Column(Text, nullable=True)            # JSON array of {item, owner, due}
    next_meeting = Column(String, nullable=True)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class PhotoLog(Base):
    """Site photo with metadata."""
    __tablename__ = "pm_photos"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    file_path   = Column(String, nullable=False)
    original_filename = Column(String, nullable=True)
    caption     = Column(String, nullable=True)
    location    = Column(String, nullable=True)
    category    = Column(String, nullable=True)          # progress | issue | safety | material | general
    taken_date  = Column(String, nullable=True)
    task_id     = Column(Integer, ForeignKey("pm_tasks.id"), nullable=True)
    punch_item_id = Column(Integer, ForeignKey("pm_punch_items.id"), nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class FundingCondition(Base):
    """Per-draw lender funding conditions — items required before funds are released."""
    __tablename__ = "funding_conditions"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id     = Column(Integer, ForeignKey("draws.id"), nullable=True, index=True)
    description = Column(Text, nullable=False)
    condition_type = Column(String, default="document")  # document | inspection | approval | insurance | other
    status      = Column(String, default="open")          # open | submitted | waived | satisfied
    required_by = Column(String, nullable=True)           # YYYY-MM-DD deadline
    satisfied_date = Column(String, nullable=True)
    notes       = Column(Text, nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class DrawCertificate(Base):
    """Inspector / consultant certificate per draw — required for lender fund release."""
    __tablename__ = "draw_certificates"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id         = Column(Integer, ForeignKey("draws.id"), nullable=True, index=True)
    cert_type       = Column(String, default="progress")  # progress | occupancy | substantial_completion | final | inspection
    certifier_name  = Column(String, nullable=True)
    certifier_firm  = Column(String, nullable=True)
    cert_date       = Column(String, nullable=True)         # YYYY-MM-DD date certified
    amount_certified = Column(Float, nullable=True)         # amount certified by consultant
    file_path       = Column(String, nullable=True)
    original_filename = Column(String, nullable=True)
    status          = Column(String, default="pending")     # pending | submitted | accepted | rejected
    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class StatutoryDeclaration(Base):
    """Per-draw statutory declaration from vendor/subcontractor."""
    __tablename__ = "statutory_declarations"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id     = Column(Integer, ForeignKey("draws.id"), nullable=True, index=True)
    vendor_name = Column(String, nullable=False)
    vendor_id   = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    declaration_date = Column(String, nullable=True)       # YYYY-MM-DD date signed
    period_end  = Column(String, nullable=True)            # period covered to
    amount      = Column(Float, nullable=True)             # amount declared
    file_path   = Column(String, nullable=True)
    status      = Column(String, default="required")       # required | received | expired | waived
    created_at  = Column(DateTime, default=datetime.utcnow)


class OwnerToken(Base):
    """Token-based owner portal access — owner sees project overview without a GC account."""
    __tablename__ = "owner_tokens"

    id          = Column(Integer, primary_key=True, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    token       = Column(String, unique=True, nullable=False, index=True)
    label       = Column(String, nullable=False)           # e.g. "BMO Construction Finance"
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active   = Column(Boolean, default=True)
    expires_at  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class PromptPaymentLog(Base):
    """Tracks Ontario Construction Act / provincial prompt-payment deadlines per draw/payment."""
    __tablename__ = "prompt_payment_logs"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id         = Column(Integer, ForeignKey("draws.id"), nullable=True)
    invoice_id      = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    payment_type    = Column(String, nullable=False)   # owner_to_gc | gc_to_sub
    proper_invoice_date = Column(String, nullable=True)   # date invoice deemed proper
    certifier_cert_date = Column(String, nullable=True)   # date consultant certified
    payment_deadline    = Column(String, nullable=True)   # calculated deadline YYYY-MM-DD
    paid_date           = Column(String, nullable=True)   # actual payment date
    is_overdue          = Column(Boolean, default=False)
    province        = Column(String, default="ON")
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)


class AuditLog(Base):
    """Org-scoped audit trail for financial actions."""
    __tablename__ = "audit_logs"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    user_id     = Column(Integer, ForeignKey("users.id"), nullable=True)
    username    = Column(String, nullable=True)
    action      = Column(String, nullable=False)       # upload_invoice | edit_invoice | delete_invoice | login | etc.
    entity_type = Column(String, nullable=True)        # invoice | project | draw | claim | member
    entity_id   = Column(Integer, nullable=True)
    detail      = Column(Text, nullable=True)          # human-readable summary
    ip_address  = Column(String, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow, index=True)


class OrgVendor(Base):
    """Organisation-level vendor/supplier directory — reusable across all projects."""
    __tablename__ = "org_vendors"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    vendor_code     = Column(String, nullable=True)       # internal ID (e.g. VEN-001)
    name            = Column(String, nullable=False)
    trade           = Column(String, nullable=True)
    contact_name    = Column(String, nullable=True)
    contact_email   = Column(String, nullable=True)
    contact_phone   = Column(String, nullable=True)
    address         = Column(String, nullable=True)
    payment_terms   = Column(String, nullable=True)       # Net 30, Net 60, etc.
    hst_number      = Column(String, nullable=True)       # GST/HST registration
    wsib_number     = Column(String, nullable=True)
    wsib_expiry     = Column(String, nullable=True)       # YYYY-MM-DD
    wcb_number      = Column(String, nullable=True)       # WCB (Alberta, BC, MB, SK)
    wcb_expiry      = Column(String, nullable=True)       # YYYY-MM-DD
    insurance_expiry        = Column(String, nullable=True)
    liability_limit         = Column(Float, nullable=True)   # general liability limit CAD
    cra_business_number     = Column(String, nullable=True)  # 9-digit BN for T5018
    province        = Column(String, nullable=True)       # ON, BC, AB, QC, etc.
    is_incorporated = Column(Boolean, default=False)      # True = incorporated; False = individual (T5018 threshold differs)
    statutory_declaration_date = Column(String, nullable=True)  # last statutory decl received
    notes           = Column(Text, nullable=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    organization = relationship("Organization", back_populates="vendors")


# ─── Project Finance Models ──────────────────────────────────────────────────

class Project(Base):
    __tablename__ = "projects"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    org_id  = Column(Integer, ForeignKey("organizations.id"), nullable=True, index=True)
    name = Column(String, nullable=False)
    code = Column(String, nullable=True)
    client = Column(String, nullable=True)
    address = Column(String, nullable=True)
    start_date = Column(String, nullable=True)
    end_date = Column(String, nullable=True)
    total_budget = Column(Float, default=0.0)
    lender_budget = Column(Float, nullable=True)        # approved budget as presented to lender (may differ)
    currency = Column(String, default="CAD")
    province    = Column(String, default="ON")          # CA province: ON, BC, AB, QC, MB, SK, NS, NB, NL, PE, YT, NT, NU
    contingency_budget = Column(Float, nullable=True)   # contingency reserve
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
    budget = Column(Float, default=0.0)              # internal budget for this category
    lender_budget = Column(Float, nullable=True)      # budget as presented to lender (None = use internal)
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


class Subcontractor(Base):
    """Vendor/subcontractor directory — contacts, contract values, insurance/WSIB status."""
    __tablename__ = "subcontractors"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    trade = Column(String, nullable=True)               # Electrical, Framing, Plumbing, etc.
    contact_name = Column(String, nullable=True)
    contact_email = Column(String, nullable=True)
    contact_phone = Column(String, nullable=True)
    contract_value = Column(Float, nullable=True)        # original contract amount
    status = Column(String, default="active")            # active | complete | terminated
    insurance_expiry = Column(String, nullable=True)     # YYYY-MM-DD
    wsib_expiry = Column(String, nullable=True)          # YYYY-MM-DD
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

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


class Milestone(Base):
    """Project schedule milestones — key dates and completion tracking."""
    __tablename__ = "milestones"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    target_date = Column(String, nullable=True)           # YYYY-MM-DD
    actual_date = Column(String, nullable=True)           # YYYY-MM-DD (filled on completion)
    pct_complete = Column(Float, default=0.0)             # 0–100
    status = Column(String, default="pending")            # pending | in_progress | complete | delayed
    display_order = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")


class LienWaiver(Base):
    """Lien waiver records — tracks receipt of conditional/unconditional waivers per trade/draw."""
    __tablename__ = "lien_waivers"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)
    subcontractor_id = Column(Integer, ForeignKey("subcontractors.id"), nullable=True)
    vendor_name = Column(String, nullable=True)           # free-text if no subcontractor record
    waiver_type = Column(String, nullable=False)          # conditional | unconditional
    amount = Column(Float, nullable=True)                 # amount covered by the waiver
    date_received = Column(String, nullable=True)         # YYYY-MM-DD
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    draw = relationship("Draw")
    subcontractor = relationship("Subcontractor")


class ProjectDocument(Base):
    """Non-invoice documents filed against a project: contracts, permits, RFIs, submittals, etc."""
    __tablename__ = "project_documents"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    doc_type = Column(String, nullable=False)    # contract | permit | rfi | submittal | drawing | report | other
    title = Column(String, nullable=False)
    file_path = Column(String, nullable=True)    # stored on disk (nullable = link-only docs)
    original_filename = Column(String, nullable=True)
    external_url = Column(String, nullable=True) # optional link instead of file
    notes = Column(Text, nullable=True)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)
    category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    user = relationship("User")


class LenderToken(Base):
    """Shareable read-only token for external lender view of a draw package."""
    __tablename__ = "lender_tokens"

    id = Column(Integer, primary_key=True, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id = Column(Integer, ForeignKey("draws.id"), nullable=True)   # None = all draws
    token = Column(String, unique=True, nullable=False, index=True)
    label = Column(String, nullable=False)              # e.g. "Draw 1 — TD Bank"
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    is_active = Column(Boolean, default=True)
    expires_at = Column(String, nullable=True)          # YYYY-MM-DD, None = never
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project")
    draw = relationship("Draw")


class GeminiApiKey(Base):
    """Admin-managed pool of Gemini API keys — tried in priority order with fallback."""
    __tablename__ = "gemini_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)        # e.g. "Primary Key", "Backup Key 1"
    key_value = Column(String, nullable=False)    # actual API key (admin-only access)
    priority = Column(Integer, default=100)       # lower number = tried first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)


# ─── Lender Risk & Finance Models ────────────────────────────────────────────

class LenderCovenant(Base):
    """Loan covenant tracking — DSCR, LTC/LTV, equity contribution triggers."""
    __tablename__ = "lender_covenants"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    covenant_type    = Column(String, nullable=False)   # ltc | ltv | dscr | equity | other
    name             = Column(String, nullable=False)
    threshold_value  = Column(Float, nullable=True)     # e.g. 0.65 for 65% LTC
    threshold_operator = Column(String, default="<=")   # <= | >= | =
    current_value    = Column(Float, nullable=True)
    as_of_date       = Column(String, nullable=True)    # YYYY-MM-DD
    status           = Column(String, default="compliant")  # compliant | warning | breach
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User")


class InterestReserve(Base):
    """Interest reserve per project — tracks total, drawn, and rate for depletion forecasting."""
    __tablename__ = "interest_reserves"

    id             = Column(Integer, primary_key=True, index=True)
    org_id         = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id     = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    reserve_amount = Column(Float, nullable=False)    # total interest reserve funded
    drawn_to_date  = Column(Float, default=0.0)       # cumulative drawn from reserve
    interest_rate  = Column(Float, nullable=True)     # annual rate %
    accrual_basis  = Column(String, default="actual/365")  # actual/365 | 30/360
    notes          = Column(Text, nullable=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)
    updated_at     = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User")
    draws   = relationship("InterestReserveDraw", back_populates="reserve", cascade="all, delete-orphan")


class InterestReserveDraw(Base):
    """Individual draw against the interest reserve."""
    __tablename__ = "interest_reserve_draws"

    id          = Column(Integer, primary_key=True, index=True)
    reserve_id  = Column(Integer, ForeignKey("interest_reserves.id"), nullable=False, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    draw_date   = Column(String, nullable=False)   # YYYY-MM-DD
    amount      = Column(Float, nullable=False)
    period_start = Column(String, nullable=True)
    period_end  = Column(String, nullable=True)
    notes       = Column(Text, nullable=True)
    created_at  = Column(DateTime, default=datetime.utcnow)

    reserve = relationship("InterestReserve", back_populates="draws")


# ─── Bond Registry ────────────────────────────────────────────────────────────

class Bond(Base):
    """Performance bond, labour & material bond, bid bond, maintenance bond registry."""
    __tablename__ = "bonds"

    id             = Column(Integer, primary_key=True, index=True)
    org_id         = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id     = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    vendor_id      = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    vendor_name    = Column(String, nullable=True)
    bond_type      = Column(String, nullable=False)  # performance | labour_material | maintenance | bid | payment
    bond_number    = Column(String, nullable=True)
    surety_company = Column(String, nullable=True)
    bond_amount    = Column(Float, nullable=True)
    effective_date = Column(String, nullable=True)   # YYYY-MM-DD
    expiry_date    = Column(String, nullable=True)   # YYYY-MM-DD
    status         = Column(String, default="active")  # active | expired | claimed | cancelled
    file_path      = Column(String, nullable=True)
    notes          = Column(Text, nullable=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


# ─── Permit & Inspection Workflow ─────────────────────────────────────────────

class Permit(Base):
    """Municipal permit register — building, electrical, plumbing, occupancy, etc."""
    __tablename__ = "permits"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    permit_type      = Column(String, nullable=False)  # building | electrical | plumbing | mechanical | demolition | occupancy | other
    permit_number    = Column(String, nullable=True)
    description      = Column(String, nullable=False)
    authority        = Column(String, nullable=True)   # issuing municipality/authority
    application_date = Column(String, nullable=True)   # YYYY-MM-DD
    issued_date      = Column(String, nullable=True)   # YYYY-MM-DD
    expiry_date      = Column(String, nullable=True)   # YYYY-MM-DD
    status           = Column(String, default="pending")  # pending | applied | issued | expired | closed | revoked
    fee_paid         = Column(Float, nullable=True)
    file_path        = Column(String, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    creator     = relationship("User")
    inspections = relationship("PermitInspection", back_populates="permit", cascade="all, delete-orphan")


class PermitInspection(Base):
    """Inspection record under a permit."""
    __tablename__ = "permit_inspections"

    id              = Column(Integer, primary_key=True, index=True)
    permit_id       = Column(Integer, ForeignKey("permits.id"), nullable=False, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False)
    inspection_type = Column(String, nullable=False)   # framing | electrical | plumbing | final | etc.
    scheduled_date  = Column(String, nullable=True)    # YYYY-MM-DD
    completed_date  = Column(String, nullable=True)    # YYYY-MM-DD
    inspector_name  = Column(String, nullable=True)
    result          = Column(String, default="pending")  # pending | passed | failed | conditional
    deficiencies    = Column(Text, nullable=True)
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    permit = relationship("Permit", back_populates="inspections")


# ─── Safety Management ────────────────────────────────────────────────────────

class SafetyIncident(Base):
    """Safety incident and near-miss reporting (COR/WSIB/MOL compliance)."""
    __tablename__ = "safety_incidents"

    id                  = Column(Integer, primary_key=True, index=True)
    org_id              = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id          = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    incident_date       = Column(String, nullable=False, index=True)
    incident_type       = Column(String, nullable=False)  # injury | near_miss | property_damage | environmental | first_aid
    severity            = Column(String, default="low")   # low | medium | high | critical
    description         = Column(Text, nullable=False)
    location            = Column(String, nullable=True)
    persons_involved    = Column(Text, nullable=True)
    immediate_actions   = Column(Text, nullable=True)
    root_cause          = Column(Text, nullable=True)
    corrective_actions  = Column(Text, nullable=True)
    wsib_reportable     = Column(Boolean, default=False)
    wsib_reported_date  = Column(String, nullable=True)
    mol_reportable      = Column(Boolean, default=False)
    mol_reported_date   = Column(String, nullable=True)
    status              = Column(String, default="open")  # open | under_investigation | closed
    created_by          = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at          = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


class ToolboxTalk(Base):
    """Toolbox talk / safety meeting record with attendance."""
    __tablename__ = "toolbox_talks"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    talk_date        = Column(String, nullable=False, index=True)
    topic            = Column(String, nullable=False)
    facilitator      = Column(String, nullable=True)
    attendee_count   = Column(Integer, default=0)
    attendees        = Column(Text, nullable=True)        # comma-separated or JSON
    duration_minutes = Column(Integer, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


# ─── Warranty Tracking ────────────────────────────────────────────────────────

class WarrantyItem(Base):
    """TARION / homeowner warranty deficiency tracking."""
    __tablename__ = "warranty_items"

    id             = Column(Integer, primary_key=True, index=True)
    org_id         = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id     = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    item_number    = Column(String, nullable=True)
    category       = Column(String, default="other")  # structural | envelope | mechanical | finishes | other
    description    = Column(Text, nullable=False)
    location       = Column(String, nullable=True)
    reported_date  = Column(String, nullable=True)    # YYYY-MM-DD
    warranty_type  = Column(String, default="1year")  # 30day | 1year | 2year | 7year | tarion
    homeowner_name = Column(String, nullable=True)
    status         = Column(String, default="open")   # open | scheduled | in_progress | resolved | disputed
    assigned_to    = Column(String, nullable=True)    # trade/vendor name
    scheduled_date = Column(String, nullable=True)
    resolved_date  = Column(String, nullable=True)
    notes          = Column(Text, nullable=True)
    created_by     = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at     = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


# ─── Labour Time Tracking ─────────────────────────────────────────────────────

class Timecard(Base):
    """Crew timecard — labour cost tracking per worker per day."""
    __tablename__ = "timecards"

    id                = Column(Integer, primary_key=True, index=True)
    org_id            = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id        = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    worker_name       = Column(String, nullable=False)
    trade             = Column(String, nullable=True)
    classification    = Column(String, nullable=True)  # journeyman | apprentice | foreman | labourer
    work_date         = Column(String, nullable=False, index=True)
    regular_hours     = Column(Float, default=0.0)
    overtime_hours    = Column(Float, default=0.0)
    double_time_hours = Column(Float, default=0.0)
    hourly_rate       = Column(Float, nullable=True)
    burden_pct        = Column(Float, default=0.0)     # labour burden %
    cost_category_id  = Column(Integer, ForeignKey("cost_categories.id"), nullable=True)
    work_description  = Column(String, nullable=True)
    created_by        = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at        = Column(DateTime, default=datetime.utcnow)

    creator  = relationship("User")
    category = relationship("CostCategory")


# ─── Bid Management / Preconstruction ────────────────────────────────────────

class BidPackage(Base):
    """A bid solicitation package — sent to subs to price a scope of work."""
    __tablename__ = "bid_packages"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    package_number  = Column(String, nullable=False)   # e.g. BP-001
    title           = Column(String, nullable=False)
    description     = Column(Text, nullable=True)
    trade_category  = Column(String, nullable=True)    # Framing, Electrical, Plumbing, etc.
    issue_date      = Column(String, nullable=True)    # YYYY-MM-DD
    due_date        = Column(String, nullable=True)    # YYYY-MM-DD
    estimated_value = Column(Float, nullable=True)     # internal estimate
    status          = Column(String, default="draft")  # draft | issued | receiving | leveled | awarded | cancelled
    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    creator   = relationship("User")
    responses = relationship("BidResponse", back_populates="package", cascade="all, delete-orphan")


class BidResponse(Base):
    """A subcontractor's bid response to a bid package."""
    __tablename__ = "bid_responses"

    id              = Column(Integer, primary_key=True, index=True)
    package_id      = Column(Integer, ForeignKey("bid_packages.id"), nullable=False, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False)
    vendor_id       = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    vendor_name     = Column(String, nullable=False)
    contact_email   = Column(String, nullable=True)
    submitted_date  = Column(String, nullable=True)   # YYYY-MM-DD
    total_amount    = Column(Float, nullable=True)
    inclusions      = Column(Text, nullable=True)     # what's included in their price
    exclusions      = Column(Text, nullable=True)     # what's excluded
    qualifications  = Column(Text, nullable=True)     # bid qualifications / clarifications
    status          = Column(String, default="invited")  # invited | submitted | shortlisted | awarded | rejected
    invite_token    = Column(String, nullable=True, index=True)  # token for self-serve bid portal
    notes           = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    package = relationship("BidPackage", back_populates="responses")


# ─── Change Order Client Approval ────────────────────────────────────────────

class COApprovalToken(Base):
    """Client-facing change order approval link — no login required."""
    __tablename__ = "co_approval_tokens"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False)
    co_id       = Column(Integer, ForeignKey("change_orders.id"), nullable=False, index=True)
    token       = Column(String, unique=True, nullable=False, index=True)
    client_name = Column(String, nullable=True)
    client_email = Column(String, nullable=True)
    approved_at = Column(DateTime, nullable=True)
    rejected_at = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    expires_at  = Column(DateTime, nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User")


# ─── Client Selections Portal ────────────────────────────────────────────────

class ClientSelectionCategory(Base):
    """Category of finish selections (Kitchen, Bathrooms, Flooring, etc.)"""
    __tablename__ = "client_selection_categories"

    id         = Column(Integer, primary_key=True, index=True)
    org_id     = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name       = Column(String, nullable=False)
    display_order = Column(Integer, default=100)
    created_at = Column(DateTime, default=datetime.utcnow)

    items = relationship("ClientSelection", back_populates="category", cascade="all, delete-orphan")


class ClientSelection(Base):
    """A single finish selection item — what the client picks."""
    __tablename__ = "client_selections"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    category_id      = Column(Integer, ForeignKey("client_selection_categories.id"), nullable=True)
    item_name        = Column(String, nullable=False)
    description      = Column(Text, nullable=True)
    standard_option  = Column(String, nullable=True)
    client_choice    = Column(String, nullable=True)
    allowance_amount = Column(Float, nullable=True)
    actual_cost      = Column(Float, nullable=True)
    upgrade_amount   = Column(Float, nullable=True)
    status           = Column(String, default="pending")  # pending | selected | confirmed | ordered | installed
    due_date         = Column(String, nullable=True)
    notes            = Column(Text, nullable=True)
    client_approved_at = Column(DateTime, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    category = relationship("ClientSelectionCategory", back_populates="items")
    sel_creator = relationship("User", foreign_keys=[created_by])


class ClientSelectionToken(Base):
    """Public token for client to view and approve their selections."""
    __tablename__ = "client_selection_tokens"

    id           = Column(Integer, primary_key=True, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=False)
    token        = Column(String, unique=True, nullable=False, index=True)
    client_name  = Column(String, nullable=True)
    client_email = Column(String, nullable=True)
    is_active    = Column(Boolean, default=True)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    sel_token_creator = relationship("User", foreign_keys=[created_by])


# ─── Equipment Management ─────────────────────────────────────────────────────

class Equipment(Base):
    """Equipment register — owned or rented plant and machinery."""
    __tablename__ = "equipment"

    id                 = Column(Integer, primary_key=True, index=True)
    org_id             = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    equipment_code     = Column(String, nullable=True)
    name               = Column(String, nullable=False)
    equipment_type     = Column(String, nullable=True)
    make               = Column(String, nullable=True)
    model              = Column(String, nullable=True)
    year               = Column(Integer, nullable=True)
    serial_number      = Column(String, nullable=True)
    ownership          = Column(String, default="owned")   # owned | rented | leased
    daily_rate         = Column(Float, nullable=True)
    hourly_rate        = Column(Float, nullable=True)
    status             = Column(String, default="available")  # available | in_use | maintenance | retired
    current_project_id = Column(Integer, ForeignKey("projects.id"), nullable=True)
    operator_name      = Column(String, nullable=True)
    next_service_date  = Column(String, nullable=True)
    insurance_expiry   = Column(String, nullable=True)
    notes              = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)

    current_project = relationship("Project", foreign_keys=[current_project_id])
    usage_logs      = relationship("EquipmentLog", back_populates="equipment", cascade="all, delete-orphan")


class EquipmentLog(Base):
    """Daily equipment usage or maintenance entry."""
    __tablename__ = "equipment_logs"

    id               = Column(Integer, primary_key=True, index=True)
    equipment_id     = Column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=True)
    log_date         = Column(String, nullable=False, index=True)
    log_type         = Column(String, default="usage")    # usage | maintenance | inspection | repair
    hours_used       = Column(Float, default=0.0)
    fuel_litres      = Column(Float, nullable=True)
    operator_name    = Column(String, nullable=True)
    work_description = Column(String, nullable=True)
    cost             = Column(Float, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    equipment     = relationship("Equipment", back_populates="usage_logs")
    eq_log_creator = relationship("User", foreign_keys=[created_by])


# ─── Lien Release Tracking ────────────────────────────────────────────────────

class LienRelease(Base):
    """Formal holdback/lien release record — progressive or annual per Construction Act."""
    __tablename__ = "lien_releases"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id          = Column(Integer, ForeignKey("draws.id"), nullable=True)
    release_type     = Column(String, nullable=False)   # progressive | annual | final | substantial_completion
    vendor_id        = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    vendor_name      = Column(String, nullable=True)
    holdback_amount  = Column(Float, nullable=True)
    lien_expiry_date = Column(String, nullable=True)    # YYYY-MM-DD
    release_date     = Column(String, nullable=True)
    payment_date     = Column(String, nullable=True)
    status           = Column(String, default="pending")  # pending | lien_period_running | cleared | released | disputed
    statutory_declaration_received = Column(Boolean, default=False)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    lien_creator = relationship("User", foreign_keys=[created_by])


# ─── Vendor Scorecard ─────────────────────────────────────────────────────────

class VendorScore(Base):
    """Vendor/subcontractor performance rating per project."""
    __tablename__ = "vendor_scores"

    id            = Column(Integer, primary_key=True, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id    = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    vendor_id     = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    vendor_name   = Column(String, nullable=False)
    period        = Column(String, nullable=True)
    quality       = Column(Integer, nullable=True)        # 1-5
    timeliness    = Column(Integer, nullable=True)
    safety_score  = Column(Integer, nullable=True)
    communication = Column(Integer, nullable=True)
    value         = Column(Integer, nullable=True)
    would_rehire  = Column(Boolean, nullable=True)
    comments      = Column(Text, nullable=True)
    rated_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    rater = relationship("User", foreign_keys=[rated_by])


# ─── AI Specification Review ──────────────────────────────────────────────────

class SpecReview(Base):
    """AI-powered spec review result — findings from Gemini analysis of specification docs."""
    __tablename__ = "spec_reviews"

    id           = Column(Integer, primary_key=True, index=True)
    org_id       = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id   = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    filename     = Column(String, nullable=True)
    status       = Column(String, default="pending")   # pending | processing | complete | error
    findings     = Column(JSON, nullable=True)          # list of {type, severity, section, description}
    summary      = Column(Text, nullable=True)
    total_issues = Column(Integer, default=0)
    created_by   = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at   = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── Drawing Register ─────────────────────────────────────────────────────────

class DrawingRegister(Base):
    """Drawing register entry — tracks revisions, status, and transmittals."""
    __tablename__ = "drawing_register"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    drawing_number  = Column(String, nullable=False)     # e.g. A-101
    title           = Column(String, nullable=False)
    discipline      = Column(String, nullable=True)      # Architectural | Structural | Mechanical | Electrical | Civil
    current_revision = Column(String, nullable=True)    # e.g. Rev 3
    revision_date   = Column(String, nullable=True)     # YYYY-MM-DD
    status          = Column(String, default="issued")  # issued | superseded | void | for_review | for_construction | record
    file_path       = Column(String, nullable=True)
    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── Subcontractor Prequalification ──────────────────────────────────────────

class SubPrequalification(Base):
    """Subcontractor prequalification record."""
    __tablename__ = "sub_prequalifications"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    vendor_id       = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    company_name    = Column(String, nullable=False)
    trade           = Column(String, nullable=True)
    contact_name    = Column(String, nullable=True)
    contact_email   = Column(String, nullable=True)
    years_in_business = Column(Integer, nullable=True)
    annual_revenue  = Column(Float, nullable=True)
    bonding_capacity = Column(Float, nullable=True)
    largest_project = Column(Float, nullable=True)
    safety_record   = Column(Text, nullable=True)   # description of safety record
    wsib_number     = Column(String, nullable=True)
    cra_bn          = Column(String, nullable=True)
    hst_number      = Column(String, nullable=True)
    references      = Column(Text, nullable=True)   # JSON array of references
    status          = Column(String, default="submitted")  # submitted | under_review | approved | rejected | expired
    notes           = Column(Text, nullable=True)
    invite_token    = Column(String, nullable=True, unique=True, index=True)
    submitted_at    = Column(DateTime, nullable=True)
    reviewed_by     = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at     = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    reviewer = relationship("User", foreign_keys=[reviewed_by])


# ─── Client Communication Hub ─────────────────────────────────────────────────

class ClientHubPost(Base):
    """Progress update post visible to the client on their portal."""
    __tablename__ = "client_hub_posts"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    title       = Column(String, nullable=False)
    body        = Column(Text, nullable=True)
    milestone   = Column(String, nullable=True)          # optional milestone name
    photo_paths = Column(JSON, nullable=True)            # list of uploaded photo paths
    visibility  = Column(String, default="client")       # client | internal | all
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


class ClientMessage(Base):
    """Message between GC team and client (homeowner)."""
    __tablename__ = "client_messages"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    sender_type = Column(String, nullable=False)         # gc | client
    sender_name = Column(String, nullable=True)
    message     = Column(Text, nullable=False)
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime, default=datetime.utcnow)


# ─── Trade Union Compliance ───────────────────────────────────────────────────

class UnionAgreement(Base):
    """Union agreement active on a project — tracks ratios, local, expiry."""
    __tablename__ = "union_agreements"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    trade            = Column(String, nullable=False)    # Electrical, Ironworkers, etc.
    local_number     = Column(String, nullable=True)     # e.g. IBEW Local 353
    agreement_type   = Column(String, default="iba")    # iba | pla | nwa | other
    apprentice_ratio = Column(String, nullable=True)     # e.g. "1:3" (1 apprentice per 3 journeymen)
    journeymen_count = Column(Integer, default=0)
    apprentice_count = Column(Integer, default=0)
    expiry_date      = Column(String, nullable=True)     # YYYY-MM-DD
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── Project Closeout ─────────────────────────────────────────────────────────

class CloseoutItem(Base):
    """Project closeout checklist item — tracks completion of handover requirements."""
    __tablename__ = "closeout_items"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    category    = Column(String, nullable=False)         # documents | warranties | inspections | financial | legal | training
    item_name   = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    responsible_party = Column(String, nullable=True)
    due_date    = Column(String, nullable=True)          # YYYY-MM-DD
    status      = Column(String, default="pending")      # pending | in_progress | complete | n_a
    completed_at = Column(DateTime, nullable=True)
    notes       = Column(Text, nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    creator = relationship("User", foreign_keys=[created_by])


# ─── Syndicated Loan Servicing ────────────────────────────────────────────────

class LoanSyndicate(Base):
    """Syndicated loan — multiple lenders sharing a single construction facility."""
    __tablename__ = "loan_syndicates"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    facility_name    = Column(String, nullable=False)
    total_commitment = Column(Float, nullable=False)
    currency         = Column(String, default="CAD")
    lead_lender      = Column(String, nullable=True)
    closing_date     = Column(String, nullable=True)
    maturity_date    = Column(String, nullable=True)
    interest_rate    = Column(Float, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    syn_creator  = relationship("User", foreign_keys=[created_by])
    participants = relationship("SyndicateParticipant", back_populates="syndicate",
                                cascade="all, delete-orphan")


class SyndicateParticipant(Base):
    """A lender's participation stake in a syndicated loan."""
    __tablename__ = "syndicate_participants"

    id                 = Column(Integer, primary_key=True, index=True)
    syndicate_id       = Column(Integer, ForeignKey("loan_syndicates.id"), nullable=False, index=True)
    org_id             = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    lender_name        = Column(String, nullable=False)
    participation_pct  = Column(Float, nullable=False)
    commitment_amount  = Column(Float, nullable=True)
    contact_name       = Column(String, nullable=True)
    contact_email      = Column(String, nullable=True)
    reporting_email    = Column(String, nullable=True)
    notes              = Column(Text, nullable=True)
    created_at         = Column(DateTime, default=datetime.utcnow)

    syndicate = relationship("LoanSyndicate", back_populates="participants")


# ─── ERP Integration Credentials ─────────────────────────────────────────────

class ERPCredential(Base):
    """ERP/accounting integration credentials — org-scoped, ready for last-mile config."""
    __tablename__ = "erp_credentials"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    erp_type         = Column(String, nullable=False)   # acumatica | cmic | sage_intacct | dynamics365 | netsuite | jonas | foundation | sage300
    label            = Column(String, nullable=False)
    endpoint_url     = Column(String, nullable=True)
    credentials      = Column(JSON, nullable=True)      # auth fields dict (type-specific)
    is_active        = Column(Boolean, default=False)
    last_sync        = Column(DateTime, nullable=True)
    last_sync_status = Column(String, nullable=True)    # success | error | pending
    sync_log         = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)
    updated_at       = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    erp_creator = relationship("User", foreign_keys=[created_by])


# ─── Subcontract Agreements ───────────────────────────────────────────────────

class SubcontractAgreement(Base):
    """Generated subcontract agreement — from awarded bid or manual entry."""
    __tablename__ = "subcontract_agreements"

    id               = Column(Integer, primary_key=True, index=True)
    org_id           = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id       = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    bid_response_id  = Column(Integer, ForeignKey("bid_responses.id"), nullable=True)
    vendor_id        = Column(Integer, ForeignKey("org_vendors.id"), nullable=True)
    vendor_name      = Column(String, nullable=False)
    trade            = Column(String, nullable=True)
    contract_number  = Column(String, nullable=True)    # e.g. SC-001
    scope_of_work    = Column(Text, nullable=True)
    inclusions       = Column(Text, nullable=True)
    exclusions       = Column(Text, nullable=True)
    contract_amount  = Column(Float, nullable=False)
    holdback_pct     = Column(Float, default=10.0)
    payment_terms    = Column(String, nullable=True)    # e.g. Net 30, Progress draws
    start_date       = Column(String, nullable=True)
    end_date         = Column(String, nullable=True)
    insurance_required = Column(Boolean, default=True)
    bond_required    = Column(Boolean, default=False)
    warranty_period  = Column(String, nullable=True)   # e.g. "1 year from substantial completion"
    dispute_resolution = Column(String, default="CCDC")  # CCDC | arbitration | litigation
    governing_law    = Column(String, nullable=True)   # province
    status           = Column(String, default="draft") # draft | issued | executed | terminated
    sign_token       = Column(String, nullable=True, unique=True, index=True)
    signed_at        = Column(DateTime, nullable=True)
    signed_by_name   = Column(String, nullable=True)
    signed_by_ip     = Column(String, nullable=True)
    notes            = Column(Text, nullable=True)
    created_by       = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at       = Column(DateTime, default=datetime.utcnow)

    sc_creator = relationship("User", foreign_keys=[created_by])


# ─── Canadian Legal Workflows ─────────────────────────────────────────────────

class NonPaymentNotice(Base):
    """Notice of Non-Payment — Ontario Construction Act / provincial prompt payment."""
    __tablename__ = "non_payment_notices"

    id                   = Column(Integer, primary_key=True, index=True)
    org_id               = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id           = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    draw_id              = Column(Integer, ForeignKey("draws.id"), nullable=True)
    invoice_id           = Column(Integer, ForeignKey("invoices.id"), nullable=True)
    payment_type         = Column(String, nullable=False)   # owner_to_gc | gc_to_sub
    proper_invoice_date  = Column(String, nullable=True)    # YYYY-MM-DD
    certifier_cert_date  = Column(String, nullable=True)    # YYYY-MM-DD
    payment_deadline     = Column(String, nullable=True)    # YYYY-MM-DD
    notice_date          = Column(String, nullable=True)    # YYYY-MM-DD (date NNP served)
    disputed_amount      = Column(Float, nullable=True)
    non_disputed_amount  = Column(Float, nullable=True)
    reasons              = Column(Text, nullable=True)       # reason codes + explanations
    vendor_name          = Column(String, nullable=True)
    vendor_address       = Column(Text, nullable=True)
    province             = Column(String, default="ON")
    status               = Column(String, default="draft")  # draft | served | withdrawn
    notes                = Column(Text, nullable=True)
    created_by           = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at           = Column(DateTime, default=datetime.utcnow)

    nnp_creator = relationship("User", foreign_keys=[created_by])


class SubstantialPerformanceCert(Base):
    """Certificate of Substantial Performance — triggers holdback release clock."""
    __tablename__ = "substantial_performance_certs"

    id                = Column(Integer, primary_key=True, index=True)
    org_id            = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id        = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    contract_amount   = Column(Float, nullable=True)
    certified_amount  = Column(Float, nullable=True)   # amount certified as substantially complete
    holdback_amount   = Column(Float, nullable=True)
    certification_date = Column(String, nullable=True)  # YYYY-MM-DD when certified
    publication_date  = Column(String, nullable=True)   # YYYY-MM-DD when published in Daily Commercial
    lien_expiry_date  = Column(String, nullable=True)   # YYYY-MM-DD (45/60 days from publication)
    holdback_release_date = Column(String, nullable=True) # YYYY-MM-DD when holdback can be released
    consultant_name   = Column(String, nullable=True)
    consultant_firm   = Column(String, nullable=True)
    owner_name        = Column(String, nullable=True)
    contractor_name   = Column(String, nullable=True)
    province          = Column(String, default="ON")
    status            = Column(String, default="draft")  # draft | certified | published | lien_running | holdback_released
    notes             = Column(Text, nullable=True)
    created_by        = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at        = Column(DateTime, default=datetime.utcnow)

    sp_creator = relationship("User", foreign_keys=[created_by])


# ─── Sources & Uses Ledger ────────────────────────────────────────────────────

class SourcesUsesEntry(Base):
    """Sources & Uses ledger — tracks equity, debt, grants vs hard/soft costs."""
    __tablename__ = "sources_uses_entries"

    id            = Column(Integer, primary_key=True, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id    = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    entry_type    = Column(String, nullable=False)     # source | use
    category      = Column(String, nullable=False)
    description   = Column(String, nullable=False)
    budgeted_amount = Column(Float, default=0.0)
    actual_amount = Column(Float, nullable=True)
    variance      = Column(Float, nullable=True)       # computed: actual - budgeted
    as_of_date    = Column(String, nullable=True)
    notes         = Column(Text, nullable=True)
    display_order = Column(Integer, default=100)
    created_by    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    su_creator = relationship("User", foreign_keys=[created_by])


# ─── Estimating Lite ──────────────────────────────────────────────────────────

class Estimate(Base):
    """Project estimate — line items grouped by CSI division."""
    __tablename__ = "estimates"

    id          = Column(Integer, primary_key=True, index=True)
    org_id      = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id  = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    name        = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    status      = Column(String, default="draft")      # draft | submitted | approved | archived
    version     = Column(Integer, default=1)
    notes       = Column(Text, nullable=True)
    created_by  = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    est_creator = relationship("User", foreign_keys=[created_by])
    line_items  = relationship("EstimateLineItem", back_populates="estimate", cascade="all, delete-orphan")


class EstimateLineItem(Base):
    """A single line item in an estimate."""
    __tablename__ = "estimate_line_items"

    id            = Column(Integer, primary_key=True, index=True)
    estimate_id   = Column(Integer, ForeignKey("estimates.id"), nullable=False, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=False)
    project_id    = Column(Integer, ForeignKey("projects.id"), nullable=False)
    division      = Column(String, nullable=True)       # CSI division e.g. "03 - Concrete"
    description   = Column(String, nullable=False)
    quantity      = Column(Float, nullable=True)
    unit          = Column(String, nullable=True)        # SF, LF, EA, CY, LS, etc.
    unit_cost     = Column(Float, nullable=True)
    total_cost    = Column(Float, nullable=True)
    cost_category_id = Column(Integer, ForeignKey("cost_categories.id"), nullable=True)
    labour_pct    = Column(Float, nullable=True)        # % of total that is labour
    material_pct  = Column(Float, nullable=True)
    subcontracted = Column(Boolean, default=False)
    notes         = Column(String, nullable=True)
    display_order = Column(Integer, default=100)
    created_at    = Column(DateTime, default=datetime.utcnow)

    estimate = relationship("Estimate", back_populates="line_items")


# ─── Quality Inspections ──────────────────────────────────────────────────────

class QualityInspection(Base):
    """Quality inspection checklist — pass/fail by area."""
    __tablename__ = "quality_inspections"

    id              = Column(Integer, primary_key=True, index=True)
    org_id          = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id      = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    inspection_date = Column(String, nullable=False, index=True)
    inspector_name  = Column(String, nullable=True)
    area_location   = Column(String, nullable=True)
    inspection_type = Column(String, nullable=False)   # rough_framing | concrete | waterproofing | electrical | plumbing | insulation | drywall | finishes | commissioning | final
    status          = Column(String, default="scheduled")  # scheduled | in_progress | passed | failed | conditional
    pass_count      = Column(Integer, default=0)
    fail_count      = Column(Integer, default=0)
    notes           = Column(Text, nullable=True)
    created_by      = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow)

    qi_creator = relationship("User", foreign_keys=[created_by])
    items      = relationship("QualityInspectionItem", back_populates="inspection", cascade="all, delete-orphan")


class QualityInspectionItem(Base):
    """Individual checklist item in a quality inspection."""
    __tablename__ = "quality_inspection_items"

    id          = Column(Integer, primary_key=True, index=True)
    inspection_id = Column(Integer, ForeignKey("quality_inspections.id"), nullable=False, index=True)
    item_description = Column(String, nullable=False)
    result      = Column(String, default="pending")    # pending | pass | fail | n_a | observation
    notes       = Column(String, nullable=True)
    display_order = Column(Integer, default=100)
    created_at  = Column(DateTime, default=datetime.utcnow)

    inspection = relationship("QualityInspection", back_populates="items")


# ─── Visitor / Site Access Log ────────────────────────────────────────────────

class VisitorLog(Base):
    """Site visitor access log — safety, security, owner/lender visits."""
    __tablename__ = "visitor_logs"

    id            = Column(Integer, primary_key=True, index=True)
    org_id        = Column(Integer, ForeignKey("organizations.id"), nullable=False, index=True)
    project_id    = Column(Integer, ForeignKey("projects.id"), nullable=False, index=True)
    visit_date    = Column(String, nullable=False, index=True)
    visitor_name  = Column(String, nullable=False)
    visitor_company = Column(String, nullable=True)
    visitor_type  = Column(String, default="other")    # owner | lender | inspector | architect | consultant | supplier | other
    purpose       = Column(String, nullable=True)
    host_name     = Column(String, nullable=True)
    time_in       = Column(String, nullable=True)      # HH:MM
    time_out      = Column(String, nullable=True)      # HH:MM
    badge_number  = Column(String, nullable=True)
    safety_orientation = Column(Boolean, default=False)  # completed site safety orientation
    notes         = Column(Text, nullable=True)
    created_by    = Column(Integer, ForeignKey("users.id"), nullable=False)
    created_at    = Column(DateTime, default=datetime.utcnow)

    vl_creator = relationship("User", foreign_keys=[created_by])
