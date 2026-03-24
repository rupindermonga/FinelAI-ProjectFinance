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

    user = relationship("User", back_populates="invoices")


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


class GeminiApiKey(Base):
    """Admin-managed pool of Gemini API keys — tried in priority order with fallback."""
    __tablename__ = "gemini_api_keys"

    id = Column(Integer, primary_key=True, index=True)
    label = Column(String, nullable=False)        # e.g. "Primary Key", "Backup Key 1"
    key_value = Column(String, nullable=False)    # actual API key (admin-only access)
    priority = Column(Integer, default=100)       # lower number = tried first
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
