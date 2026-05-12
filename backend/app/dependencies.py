from fastapi import Depends, HTTPException, Header, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError, jwt
from typing import Optional, Tuple
import os
import secrets
import logging

from .database import get_db
from .models import User, Organization, OrganizationMember

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

_INSECURE_DEFAULTS = {"change-this-secret", "change-this-to-a-long-random-secret-string", ""}
_raw_secret = os.getenv("JWT_SECRET", "")
if _raw_secret in _INSECURE_DEFAULTS:
    SECRET_KEY = secrets.token_hex(32)
    logger.warning(
        "JWT_SECRET is not set or uses a placeholder — generated a random secret. "
        "Tokens will NOT survive server restarts. "
        "Set a strong JWT_SECRET in your .env file for persistence."
    )
else:
    SECRET_KEY = _raw_secret
ALGORITHM = os.getenv("JWT_ALGORITHM", "HS256")


_gemini_key_index = 0
_gemini_key_failures: dict = {}   # key -> unix timestamp of last 429
_GEMINI_COOLDOWN_SEC = 65         # how long a free key stays in cooldown after a 429


def _free_gemini_keys() -> list[str]:
    multi = os.getenv("GEMINI_API_KEYS", "")
    if multi:
        return [k.strip() for k in multi.split(",") if k.strip()]
    single = os.getenv("GEMINI_API_KEY", "").strip()
    return [single] if single else []


def _paid_gemini_key() -> str:
    return os.getenv("GEMINI_PAID_KEY", "").strip()


def get_gemini_key() -> str:
    """Return the next available free key (round-robin, skipping keys in cooldown).
    Falls back to the paid key only when all free keys are in cooldown.
    Raises HTTPException(503) if no keys are available at all."""
    global _gemini_key_index
    import time
    now = time.time()
    free = _free_gemini_keys()

    if free:
        # Try up to len(free) candidates in round-robin order, skipping cooled-down ones
        for _ in range(len(free)):
            key = free[_gemini_key_index % len(free)]
            _gemini_key_index += 1
            if now - _gemini_key_failures.get(key, 0) >= _GEMINI_COOLDOWN_SEC:
                return key

    # All free keys in cooldown — use paid key if available
    paid = _paid_gemini_key()
    if paid:
        return paid

    raise HTTPException(status_code=503, detail="All Gemini API keys are rate-limited. Try again shortly.")


def mark_gemini_key_failed(key: str) -> None:
    """Call this when a Gemini request returns 429 so the key enters cooldown."""
    import time
    _gemini_key_failures[key] = time.time()


async def call_gemini_api(payload: dict, timeout: int = 60) -> dict:
    """
    Central Gemini API caller with automatic key rotation and paid-key fallback.
    - Tries free keys round-robin, skipping any in cooldown.
    - On 429 from a free key: marks it failed, immediately retries with next key.
    - When all free keys exhausted: falls back to GEMINI_PAID_KEY.
    - Returns parsed JSON response dict.
    - Raises HTTPException on unrecoverable errors.
    """
    import httpx, time

    model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
    base_url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key="
    free = _free_gemini_keys()
    paid = _paid_gemini_key()

    if not free and not paid:
        raise HTTPException(503, "No Gemini API key configured. Set GEMINI_API_KEYS in Doppler.")

    now = time.time()
    attempted: set[str] = set()

    # --- Attempt each free key ---
    for _ in range(len(free) + 1):   # +1 to allow one full sweep
        key = get_gemini_key()        # honours cooldown + round-robin
        if key == paid:
            break                     # fell through to paid — handle below
        if key in attempted:
            continue
        attempted.add(key)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.post(base_url + key, json=payload)

            if resp.status_code == 429:
                mark_gemini_key_failed(key)
                continue             # try next free key

            resp.raise_for_status()
            return resp.json()

        except httpx.TimeoutException:
            mark_gemini_key_failed(key)
            continue

    # --- Paid key fallback ---
    if paid:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(base_url + paid, json=payload)

        if resp.status_code == 429:
            raise HTTPException(429, "All Gemini keys exhausted including paid key. Try again later.")

        resp.raise_for_status()
        return resp.json()

    raise HTTPException(503, "All Gemini API keys are rate-limited. Try again shortly.")


def require_project_access(db: Session, project_id: int, org_id: int):
    """Verify that the project exists and belongs to the requesting org. Returns project."""
    from .models import Project
    if project_id is None or project_id < 1:
        raise HTTPException(status_code=404, detail="Project not found")
    proj = db.query(Project).filter(Project.id == project_id, Project.org_id == org_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")
    return proj


def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id: int = payload.get("sub")
        if user_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == int(user_id)).first()
    if user is None or not user.is_active:
        raise credentials_exception
    # Attach primary org_id so routes can use current_user.org_id directly
    if not hasattr(user, '_org_id_cached'):
        mem = db.query(OrganizationMember).filter(
            OrganizationMember.user_id == user.id,
            OrganizationMember.is_active == True,
        ).order_by(OrganizationMember.id).first()
        user.org_id = mem.org_id if mem else None
        user._org_id_cached = True
    return user


def get_current_org(
    x_organization_id: Optional[int] = Header(None, alias="X-Organization-Id"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Tuple[Organization, OrganizationMember]:
    """Resolve the active organization for this request.

    Client sends X-Organization-Id header.  If omitted, falls back to the
    user's first active membership (covers single-org accounts transparently).
    Returns (org, membership) tuple so callers can check the user's role.
    Super-admins (is_admin=True) can access any org.
    """
    if x_organization_id:
        if current_user.is_admin:
            # Super-admin can peek into any org
            org = db.query(Organization).filter(
                Organization.id == x_organization_id,
                Organization.is_active == True,
            ).first()
            if not org:
                raise HTTPException(status_code=404, detail="Organization not found")
            mem = db.query(OrganizationMember).filter(
                OrganizationMember.org_id == x_organization_id,
                OrganizationMember.user_id == current_user.id,
            ).first()
            if not mem:
                # Super-admin gets synthetic owner membership if not already a member
                mem = OrganizationMember(
                    org_id=org.id, user_id=current_user.id, role="owner", is_active=True
                )
            return org, mem

        mem = db.query(OrganizationMember).filter(
            OrganizationMember.org_id == x_organization_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        ).first()
        if not mem:
            raise HTTPException(status_code=403, detail="Not a member of this organization")
        org = db.query(Organization).filter(
            Organization.id == x_organization_id,
            Organization.is_active == True,
        ).first()
        if not org:
            raise HTTPException(status_code=404, detail="Organization not found")
        return org, mem

    # No header — fall back to user's primary org
    mem = (
        db.query(OrganizationMember)
        .filter(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
        .order_by(OrganizationMember.created_at)
        .first()
    )
    if not mem:
        raise HTTPException(
            status_code=404,
            detail="No organization found. Ask your admin to add you to an organization.",
        )
    org = db.query(Organization).filter(
        Organization.id == mem.org_id,
        Organization.is_active == True,
    ).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found or inactive")
    return org, mem


def require_org_role(*roles: str):
    """Factory for role-checking dependencies. Usage: Depends(require_org_role('owner','admin'))"""
    def _checker(
        org_ctx: Tuple[Organization, OrganizationMember] = Depends(get_current_org),
    ) -> Tuple[Organization, OrganizationMember]:
        org, mem = org_ctx
        if mem.role not in roles:
            raise HTTPException(
                status_code=403,
                detail=f"This action requires one of these roles: {', '.join(roles)}",
            )
        return org, mem
    return _checker


# ── Module access helpers ─────────────────────────────────────────────────────

# Strict silos: finance_admin/finance_viewer see Finance only (no PM).
# pm_admin/pm_viewer see PM only (no Finance).
# site_supervisor = PM write + Finance read (field supervisor who needs budget visibility).
# editor/viewer = both modules (general staff).
FINANCE_READ_ROLES  = {"owner","admin","finance_admin","finance_viewer","site_supervisor","editor","viewer"}
FINANCE_WRITE_ROLES = {"owner","admin","finance_admin","editor"}
PM_READ_ROLES       = {"owner","admin","pm_admin","pm_viewer","site_supervisor","vendor_pm","editor","viewer"}
PM_WRITE_ROLES      = {"owner","admin","pm_admin","site_supervisor","vendor_pm","editor"}
VENDOR_FINANCE_ROLES = {"vendor_finance"}
VENDOR_PM_ROLES      = {"vendor_pm"}

def can_access_finance(role: str) -> bool:
    return role in FINANCE_READ_ROLES

def can_write_finance(role: str) -> bool:
    return role in FINANCE_WRITE_ROLES

def can_access_pm(role: str) -> bool:
    return role in PM_READ_ROLES

def is_vendor(role: str) -> bool:
    return role in VENDOR_FINANCE_ROLES | VENDOR_PM_ROLES


def require_org_member(db: Session, org_id: int, user_id: int, allowed_roles: set) -> OrganizationMember:
    """Check that user is an active member of org_id with one of allowed_roles. Super-admins pass."""
    from .models import User as _User
    user = db.query(_User).filter(_User.id == user_id).first()
    if user and user.is_admin:
        # Super-admin: synthetic owner role
        mem = db.query(OrganizationMember).filter(
            OrganizationMember.org_id == org_id,
            OrganizationMember.user_id == user_id,
        ).first()
        return mem or OrganizationMember(org_id=org_id, user_id=user_id, role="owner", is_active=True)

    mem = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org_id,
        OrganizationMember.user_id == user_id,
        OrganizationMember.is_active == True,
    ).first()
    if not mem:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
    if mem.role not in allowed_roles:
        raise HTTPException(status_code=403, detail=f"Role '{mem.role}' cannot perform this action")
    return mem
