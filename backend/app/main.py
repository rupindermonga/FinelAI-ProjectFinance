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
from .routes import auth, invoices, upload, columns, export, categories, admin, project


def _run_migrations():
    """Add any missing columns to existing tables (safe to run on every start)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE category_configs ADD COLUMN requires_sub_division BOOLEAN DEFAULT 0",
            "ALTER TABLE column_configs ADD COLUMN is_exportable BOOLEAN DEFAULT 1",
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
            "ALTER TABLE invoices ADD COLUMN payment_status VARCHAR DEFAULT 'unpaid'",
            "ALTER TABLE invoices ADD COLUMN amount_paid FLOAT DEFAULT 0.0",
            "ALTER TABLE invoices ADD COLUMN billed_to VARCHAR",
            "ALTER TABLE invoices ADD COLUMN billing_type VARCHAR",
            "ALTER TABLE invoices ADD COLUMN vendor_on_record VARCHAR",
            "ALTER TABLE invoices ADD COLUMN draw_id INTEGER REFERENCES draws(id)",
            "ALTER TABLE invoices ADD COLUMN claim_id INTEGER REFERENCES claims(id)",
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
            "style-src 'self' 'unsafe-inline' https://cdnjs.cloudflare.com https://cdn.tailwindcss.com; "
            "font-src 'self' https://cdnjs.cloudflare.com; "
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

# Serve static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    # API routes take priority (handled above); everything else serves the SPA
    _blocked = {"api/", "static/", "docs", "redoc", "openapi.json"}
    if any(full_path.startswith(b) or full_path == b for b in _blocked):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)
