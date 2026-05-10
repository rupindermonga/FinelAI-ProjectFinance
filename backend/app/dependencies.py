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

FINANCE_READ_ROLES  = {"owner","admin","finance_admin","finance_viewer","editor","viewer"}
FINANCE_WRITE_ROLES = {"owner","admin","finance_admin","editor"}
PM_READ_ROLES       = {"owner","admin","pm_admin","pm_viewer","site_supervisor","vendor_pm","finance_admin","editor","viewer"}
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
