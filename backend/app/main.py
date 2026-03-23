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
from .routes import auth, invoices, upload, columns, export, categories, admin


def _run_migrations():
    """Add any missing columns to existing tables (safe to run on every start)."""
    from sqlalchemy import text
    with engine.connect() as conn:
        for stmt in [
            "ALTER TABLE category_configs ADD COLUMN requires_sub_division BOOLEAN DEFAULT 0",
            "ALTER TABLE column_configs ADD COLUMN is_exportable BOOLEAN DEFAULT 1",
            "ALTER TABLE users ADD COLUMN is_admin BOOLEAN DEFAULT 0",
        ]:
            try:
                conn.execute(text(stmt))
                conn.commit()
            except Exception:
                pass  # Column already exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
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


app = FastAPI(
    title="Finel AI Invoice Extractor",
    description="AI-powered invoice extraction using Google Gemini",
    version="1.0.0",
    lifespan=lifespan,
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

# Serve static frontend
static_dir = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/", include_in_schema=False)
@app.get("/{full_path:path}", include_in_schema=False)
async def serve_spa(full_path: str = ""):
    # API routes take priority (handled above); everything else serves the SPA
    if full_path.startswith("api/") or full_path.startswith("static/"):
        from fastapi import HTTPException
        raise HTTPException(status_code=404)
    index_path = os.path.join(static_dir, "index.html")
    return FileResponse(index_path)
