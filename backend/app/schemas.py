from pydantic import BaseModel, EmailStr
from typing import Optional, Any, List, Literal
from datetime import datetime

VALID_FIELD_TYPES = ("string", "number", "date", "boolean")


# ─── Auth ────────────────────────────────────────────────────────────────────

class UserCreate(BaseModel):
    username: str
    email: str
    password: str

class UserLogin(BaseModel):
    username: str
    password: str

class UserOut(BaseModel):
    id: int
    username: str
    email: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ─── Column Config ────────────────────────────────────────────────────────────

class ColumnConfigCreate(BaseModel):
    field_key: str
    field_label: str
    field_description: Optional[str] = None
    field_type: Literal["string", "number", "date", "boolean"] = "string"
    display_order: Optional[int] = 100

class ColumnConfigUpdate(BaseModel):
    field_label: Optional[str] = None
    field_description: Optional[str] = None
    field_type: Optional[Literal["string", "number", "date", "boolean"]] = None
    is_active: Optional[bool] = None
    display_order: Optional[int] = None

class ColumnConfigOut(BaseModel):
    id: int
    field_key: str
    field_label: str
    field_description: Optional[str]
    field_type: str
    is_active: bool
    is_system: bool
    display_order: int

    class Config:
        from_attributes = True


# ─── Invoice ──────────────────────────────────────────────────────────────────

class InvoiceOut(BaseModel):
    id: int
    source: str
    source_file: Optional[str]
    original_filename: Optional[str]
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
