from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, Any, List, Literal
from datetime import datetime
import re

VALID_FIELD_TYPES = ("string", "number", "date", "boolean")

_USERNAME_RE = re.compile(r"^[a-zA-Z0-9_\-]+$")
_FIELD_KEY_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9_]*$")


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=128)

    @field_validator("username")
    @classmethod
    def username_alphanumeric(cls, v: str) -> str:
        if not _USERNAME_RE.match(v):
            raise ValueError("Username may only contain letters, digits, underscores, and hyphens")
        return v

class UserLogin(BaseModel):
    username: str = Field(..., min_length=1, max_length=50)
    password: str = Field(..., min_length=1, max_length=128)

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    is_admin: bool = False
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ─── Column Config ────────────────────────────────────────────────────────────

class ColumnConfigCreate(BaseModel):
    field_key: str = Field(..., min_length=1, max_length=64)
    field_label: str

    @field_validator("field_key")
    @classmethod
    def field_key_safe(cls, v: str) -> str:
        if not _FIELD_KEY_RE.match(v):
            raise ValueError("field_key must start with a letter and contain only letters, digits, and underscores")
        return v
    field_description: Optional[str] = None
    field_type: Literal["string", "number", "date", "boolean"] = "string"
    display_order: Optional[int] = 100

class ColumnConfigUpdate(BaseModel):
    field_label: Optional[str] = None
    field_description: Optional[str] = None
    field_type: Optional[Literal["string", "number", "date", "boolean"]] = None
    is_active: Optional[bool] = None
    is_exportable: Optional[bool] = None
    display_order: Optional[int] = None

class ColumnConfigOut(BaseModel):
    id: int
    field_key: str
    field_label: str
    field_description: Optional[str]
    field_type: str
    is_active: bool
    is_system: bool
    is_exportable: bool = True
    display_order: int

    class Config:
        from_attributes = True


# ─── Admin ────────────────────────────────────────────────────────────────────

class ApiKeyCreate(BaseModel):
    label: str
    key_value: str
    priority: int = 100
    is_active: bool = True

class ApiKeyUpdate(BaseModel):
    label: Optional[str] = None
    priority: Optional[int] = None
    is_active: Optional[bool] = None

class ApiKeyOut(BaseModel):
    id: int
    label: str
    key_preview: str   # masked — never the full key
    priority: int
    is_active: bool
    created_at: datetime


# ─── Invoice ──────────────────────────────────────────────────────────────────

class InvoiceOut(BaseModel):
    id: int
    source: str
    original_filename: Optional[str]   # basename only — never the server path
    source_email: Optional[str]
    processed_at: datetime
    status: str
    error_message: Optional[str]
    confidence_score: Optional[float]
    invoice_number: Optional[str]
    invoice_date: Optional[str]
    due_date: Optional[str]
    vendor_name: Optional[str]
    currency: Optional[str]
    total_due: Optional[float]
    extracted_data: Optional[Any]
    payment_status: Optional[str] = "unpaid"
    amount_paid: Optional[float] = 0.0

    class Config:
        from_attributes = True

class InvoiceListResponse(BaseModel):
    items: List[InvoiceOut]
    total: int
    page: int
    limit: int
    pages: int


# ─── Export ───────────────────────────────────────────────────────────────────

class ExportRequest(BaseModel):
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    vendor: Optional[str] = None
    currency: Optional[str] = None
    status: Optional[str] = None
    format: str = "excel"  # excel | json


# ─── Project Finance ─────────────────────────────────────────────────────────

class ProjectCreate(BaseModel):
    name: str
    code: Optional[str] = None
    client: Optional[str] = None
    address: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: float = 0.0
    currency: str = "CAD"

class ProjectUpdate(BaseModel):
    name: Optional[str] = None
    code: Optional[str] = None
    client: Optional[str] = None
    address: Optional[str] = None
    start_date: Optional[str] = None
    end_date: Optional[str] = None
    total_budget: Optional[float] = None
    currency: Optional[str] = None

class ProjectOut(BaseModel):
    id: int
    name: str
    code: Optional[str]
    client: Optional[str]
    address: Optional[str]
    start_date: Optional[str]
    end_date: Optional[str]
    total_budget: float
    currency: str
    created_at: datetime
    class Config:
        from_attributes = True

class SubDivisionOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: Optional[str]
    display_order: int
    class Config:
        from_attributes = True

class CostSubCategoryOut(BaseModel):
    id: int
    category_id: int
    name: str
    description: Optional[str]
    budget: Optional[float]
    display_order: int
    class Config:
        from_attributes = True

class CostCategoryOut(BaseModel):
    id: int
    project_id: int
    name: str
    budget: float
    is_per_subdivision: bool
    display_order: int
    sub_categories: List[CostSubCategoryOut] = []
    class Config:
        from_attributes = True

class CostCategoryCreate(BaseModel):
    name: str
    budget: float = 0.0
    is_per_subdivision: bool = False

class CostCategoryUpdate(BaseModel):
    name: Optional[str] = None
    budget: Optional[float] = None

class CostSubCategoryCreate(BaseModel):
    name: str
    description: Optional[str] = None
    budget: Optional[float] = None

class SubDivisionBudgetSet(BaseModel):
    subdivision_id: int
    budget: float

class AllocationCreate(BaseModel):
    invoice_id: int
    category_id: int
    sub_category_id: Optional[int] = None
    subdivision_id: Optional[int] = None
    percentage: float = 100.0

class AllocationOut(BaseModel):
    id: int
    invoice_id: int
    category_id: int
    sub_category_id: Optional[int]
    subdivision_id: Optional[int]
    percentage: float
    amount: float
    category_name: Optional[str] = None
    sub_category_name: Optional[str] = None
    subdivision_name: Optional[str] = None
    class Config:
        from_attributes = True

class PaymentCreate(BaseModel):
    invoice_id: int
    amount: float
    payment_date: str
    method: Optional[str] = None
    reference: Optional[str] = None
    notes: Optional[str] = None

class PaymentOut(BaseModel):
    id: int
    invoice_id: int
    amount: float
    payment_date: str
    method: Optional[str]
    reference: Optional[str]
    notes: Optional[str]
    created_at: datetime
    class Config:
        from_attributes = True
