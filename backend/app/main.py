from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from starlette.middleware.base import BaseHTTPMiddleware
from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

load_dotenv()

from .database import engine, Base
from .routes import auth, invoices, upload, columns, export, categories, admin, project, filetools


def _run_migrations():
    """Add any missing columns to existing tables (safe to run on every start)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE category_configs ADD COLUMN requires_sub_division BOOLEAN DEFAULT 0",
            "ALTER TABLE column_configs ADD COLUMN is_exportable BOOLEAN DEFAULT 1",
            "ALTER TABLE column_configs ADD COLUMN is_viewable BOOLEAN DEFAULT 1",
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN payment_status VARCHAR DEFAULT 'unpaid'",
            "ALTER TABLE invoices ADD COLUMN amount_paid FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN billed_to VARCHAR",
            "ALTER TABLE invoices ADD COLUMN billing_type VARCHAR",
            "ALTER TABLE invoices ADD COLUMN vendor_on_record VARCHAR",
            "ALTER TABLE invoices ADD COLUMN draw_id INTEGER REFERENCES draws(id)",
            "ALTER TABLE invoices ADD COLUMN claim_id INTEGER REFERENCES claims(id)",
            # Dual claim FKs
            "ALTER TABLE invoices ADD COLUMN provincial_claim_id INTEGER REFERENCES claims(id)",
            "ALTER TABLE invoices ADD COLUMN federal_claim_id INTEGER REFERENCES claims(id)",
            # Tax breakdown
            "ALTER TABLE invoices ADD COLUMN subtotal FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_gst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_hst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_qst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_pst FLOAT",
            "ALTER TABLE invoices ADD COLUMN tax_total FLOAT",
            "ALTER TABLE invoices ADD COLUMN vendor_province VARCHAR",
            # Cost tracking
            "ALTER TABLE invoices ADD COLUMN received_total FLOAT",
            "ALTER TABLE invoices ADD COLUMN lender_margin_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN lender_margin_amt FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN lender_submitted_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN lender_approved_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN lender_status VARCHAR DEFAULT 'pending'",
            "ALTER TABLE invoices ADD COLUMN lender_tax_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN govt_margin_pct FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN govt_margin_amt FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN govt_submitted_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN govt_approved_amt FLOAT",
            "ALTER TABLE invoices ADD COLUMN govt_status VARCHAR DEFAULT 'pending'",
            "ALTER TABLE invoices ADD COLUMN is_payroll BOOLEAN DEFAULT 0",
            "ALTER TABLE users ADD COLUMN is_demo BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN project_id INTEGER REFERENCES projects(id)",
            "ALTER TABLE invoices ADD COLUMN holdback_pct REAL DEFAULT 10.0",
            "ALTER TABLE invoices ADD COLUMN holdback_released BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN holdback_released_date TEXT",
            "ALTER TABLE invoices ADD COLUMN approval_status TEXT DEFAULT 'pending'",
            "ALTER TABLE invoices ADD COLUMN approved_by TEXT",
            "ALTER TABLE invoices ADD COLUMN approved_at TEXT",
            """CREATE TABLE IF NOT EXISTS milestones (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                description TEXT,
                target_date TEXT,
                actual_date TEXT,
                pct_complete REAL DEFAULT 0,
                status TEXT DEFAULT 'pending',
                display_order INTEGER DEFAULT 100,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS lien_waivers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                subcontractor_id INTEGER REFERENCES subcontractors(id),
                vendor_name TEXT,
                waiver_type TEXT NOT NULL,
                amount REAL,
                date_received TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS project_documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                user_id INTEGER NOT NULL REFERENCES users(id),
                doc_type TEXT NOT NULL DEFAULT 'other',
                title TEXT NOT NULL,
                file_path TEXT,
                original_filename TEXT,
                external_url TEXT,
                notes TEXT,
                draw_id INTEGER REFERENCES draws(id),
                category_id INTEGER REFERENCES cost_categories(id),
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS lender_tokens (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                draw_id INTEGER REFERENCES draws(id),
                token TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                created_by INTEGER NOT NULL REFERENCES users(id),
                is_active INTEGER DEFAULT 1,
                expires_at TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS subcontractors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                name TEXT NOT NULL,
                trade TEXT,
                contact_name TEXT,
                contact_email TEXT,
                contact_phone TEXT,
                contract_value REAL,
                status TEXT DEFAULT 'active',
                insurance_expiry TEXT,
                wsib_expiry TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS committed_costs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category_id INTEGER REFERENCES cost_categories(id),
                vendor TEXT NOT NULL,
                description TEXT,
                contract_amount REAL NOT NULL,
                invoiced_to_date REAL DEFAULT 0,
                status TEXT DEFAULT 'active',
                contract_date TEXT,
                expected_completion TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
            """CREATE TABLE IF NOT EXISTS change_orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id INTEGER NOT NULL REFERENCES projects(id),
                category_id INTEGER REFERENCES cost_categories(id),
                co_number TEXT NOT NULL,
                description TEXT NOT NULL,
                amount REAL NOT NULL,
                status TEXT DEFAULT 'pending',
                issued_by TEXT,
                date TEXT,
                notes TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists


def _retire_default_admin():
    """Block login with the old default password 'admin123' by rehashing to a random value."""
    from passlib.context import CryptContext
    from .database import SessionLocal
    from .models import User
    pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")
    db = SessionLocal()
    try:
        admin = db.query(User).filter(User.username == "admin").first()
        if admin and pwd.verify("admin123", admin.hashed_password):
            new_pw = os.getenv("ADMIN_PASSWORD", "")
            if new_pw and new_pw != "admin123" and len(new_pw) >= 8:
                admin.hashed_password = pwd.hash(new_pw)
                db.commit()
                print("INFO: Admin password updated from .env ADMIN_PASSWORD.")
            else:
                import secrets
                admin.hashed_password = pwd.hash(secrets.token_urlsafe(32))
                db.commit()
                print("WARNING: Admin 'admin123' password retired. Set ADMIN_PASSWORD in .env and re-run create_admin.py.")
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    _retire_default_admin()
    os.makedirs(os.getenv("UPLOAD_FOLDER", "./uploads"), exist_ok=True)
    yield


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-eval' 'unsafe-inline' "
            "https://cdn.tailwindcss.com https://cdn.jsdelivr.net; "
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com "
            "https://cdn.tailwindcss.com https://cdn.jsdelivr.net "
            "https://fonts.googleapis.com; "
            "font-src 'self' https://cdnjs.cloudflare.com https://fonts.gstatic.com; "
            "img-src 'self' data: blob:; "
            "object-src blob:; "
            "frame-src blob:; "
            "connect-src 'self'; "
            "frame-ancestors 'none';"
        )
        return response


_disable_docs = os.getenv("DISABLE_DOCS", "true").lower() in ("1", "true", "yes")

app = FastAPI(
    title="Finel AI Invoice Extractor",
    description="AI-powered invoice extraction using Google Gemini",
    version="1.0.0",
    lifespan=lifespan,
    docs_url=None if _disable_docs else "/docs",
    redoc_url=None if _disable_docs else "/redoc",
    openapi_url=None if _disable_docs else "/openapi.json",
)

app.add_middleware(SecurityHeadersMiddleware)

_raw_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000")
_allowed_origins = [o.strip() for o in _raw_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

# API routes
app.include_router(auth.router)
app.include_router(invoices.router)
app.include_router(upload.router)
app.include_router(columns.router)
app.include_router(categories.router)
app.include_router(export.router)
app.include_router(admin.router)
app.include_router(project.router)
app.include_router(project._lender_router)
app.include_router(filetools.router)

# Serve static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/lender/{token}", include_in_schema=False)
async def lender_view(token: str):
    """Serve the public lender HTML page (token is handled client-side)."""
    return FileResponse(os.path.join(static_dir, "lender.html"))


@app.get("/report", include_in_schema=False)
async def report_view():
    """Serve the internal project status report page (auth required client-side)."""
    return FileResponse(os.path.join(static_dir, "report.html"))


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    _blocked = {"api/", "static/", "docs", "redoc", "openapi.json", "lender/", "report"}
    if any(full_path.startswith(b) or full_path == b for b in _blocked):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)
