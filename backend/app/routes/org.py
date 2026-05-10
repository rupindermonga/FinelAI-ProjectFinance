"""Organisation management: CRUD, members, roles, and org-level vendor directory."""
import re, secrets
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import Organization, OrganizationMember, OrgVendor, User, Project, Invoice, OrgInvitation
from ..schemas import (
    OrgCreate, OrgUpdate, OrgOut, OrgMemberOut, OrgMemberUpdate,
    OrgVendorCreate, OrgVendorOut,
)
from ..dependencies import get_current_user, get_current_org, require_org_role
from .audit import log as audit_log

router = APIRouter(prefix="/api/org", tags=["org"])

_SLUG_RE = re.compile(r"^[a-z0-9][a-z0-9\-]{1,48}[a-z0-9]$")

ROLES = ("owner", "admin", "editor", "viewer")


# ─── Helpers ─────────────────────────────────────────────────────────────────

def _member_out(m: OrganizationMember) -> dict:
    u = m.user
    return {
        "id": m.id, "org_id": m.org_id, "user_id": m.user_id,
        "username": u.username if u else "", "email": u.email if u else "",
        "role": m.role, "is_active": m.is_active, "created_at": str(m.created_at),
    }


def _org_stats(org: Organization, db: Session) -> dict:
    member_count  = db.query(OrganizationMember).filter(OrganizationMember.org_id == org.id, OrganizationMember.is_active == True).count()
    project_count = db.query(Project).filter(Project.org_id == org.id).count()
    invoice_count = db.query(Invoice).filter(Invoice.org_id == org.id).count()
    return {"member_count": member_count, "project_count": project_count, "invoice_count": invoice_count}


# ─── List user's orgs ─────────────────────────────────────────────────────────

@router.get("")
def list_my_orgs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all orgs the current user belongs to."""
    memberships = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.user_id == current_user.id, OrganizationMember.is_active == True)
        .order_by(OrganizationMember.created_at)
        .all()
    )
    result = []
    for m in memberships:
        org = db.query(Organization).filter(Organization.id == m.org_id, Organization.is_active == True).first()
        if org:
            result.append({
                "id": org.id, "name": org.name, "slug": org.slug, "plan": org.plan,
                "is_active": org.is_active, "created_at": str(org.created_at),
                "role": m.role,
            })
    return result


# ─── Create org ───────────────────────────────────────────────────────────────

@router.post("", response_model=OrgOut)
def create_org(
    body: OrgCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a new organization. The creator becomes the owner."""
    existing = db.query(Organization).filter(Organization.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="An organization with this slug already exists")

    org = Organization(name=body.name, slug=body.slug)
    db.add(org)
    db.flush()

    # Make creator an owner
    mem = OrganizationMember(org_id=org.id, user_id=current_user.id, role="owner")
    db.add(mem)
    db.commit()
    db.refresh(org)
    return org


# ─── Get org ──────────────────────────────────────────────────────────────────

@router.get("/current")
def get_current_org_detail(
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    """Return the current org with stats."""
    org, mem = org_ctx
    data = {
        "id": org.id, "name": org.name, "slug": org.slug, "plan": org.plan,
        "is_active": org.is_active, "created_at": str(org.created_at),
        "my_role": mem.role,
    }
    data.update(_org_stats(org, db))
    return data


@router.put("/current")
def update_org(
    body: OrgUpdate,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    """Update org name / plan. Requires owner or admin role."""
    org, _ = org_ctx
    if body.name is not None:
        org.name = body.name
    if body.plan is not None:
        org.plan = body.plan
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "slug": org.slug, "plan": org.plan}


# ─── Members ──────────────────────────────────────────────────────────────────

@router.get("/members")
def list_members(
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    """List all members of the current org."""
    org, _ = org_ctx
    members = (
        db.query(OrganizationMember)
        .filter(OrganizationMember.org_id == org.id)
        .order_by(OrganizationMember.created_at)
        .all()
    )
    return [_member_out(m) for m in members]


@router.post("/members")
def add_member(
    body: dict,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Add an existing user to the org by username or email. Requires owner/admin role."""
    org, _ = org_ctx
    role = body.get("role", "editor")
    if role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLES)}")

    # Find user
    identifier = body.get("username") or body.get("email")
    if not identifier:
        raise HTTPException(status_code=400, detail="username or email required")
    target = (
        db.query(User)
        .filter((User.username == identifier) | (User.email == identifier))
        .first()
    )
    if not target:
        raise HTTPException(status_code=404, detail=f"User '{identifier}' not found")

    # Already a member?
    existing = db.query(OrganizationMember).filter(
        OrganizationMember.org_id == org.id,
        OrganizationMember.user_id == target.id,
    ).first()
    if existing:
        if not existing.is_active:
            existing.is_active = True
            existing.role = role
            db.commit()
            return _member_out(existing)
        raise HTTPException(status_code=400, detail="User is already a member of this organization")

    mem = OrganizationMember(
        org_id=org.id, user_id=target.id, role=role,
        invited_by=current_user.id,
    )
    db.add(mem)
    db.commit()
    db.refresh(mem)
    audit_log(db, org.id, current_user, "add_member", entity_type="organization_member",
              entity_id=mem.id, detail=f"Added '{target.username}' to org as {role}")
    return _member_out(mem)


@router.put("/members/{member_id}")
def update_member_role(
    member_id: int,
    body: OrgMemberUpdate,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Change a member's role or deactivate them. Owner role cannot be changed by non-owners."""
    org, acting_mem = org_ctx
    mem = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.org_id == org.id,
    ).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Member not found")

    # Prevent removing the last owner
    if mem.role == "owner" and body.role != "owner":
        owner_count = db.query(OrganizationMember).filter(
            OrganizationMember.org_id == org.id,
            OrganizationMember.role == "owner",
            OrganizationMember.is_active == True,
        ).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot change role of the last owner")

    if body.role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLES)}")

    mem.role = body.role
    if body.is_active is not None:
        mem.is_active = body.is_active
    db.commit()
    db.refresh(mem)
    return _member_out(mem)


@router.delete("/members/{member_id}")
def remove_member(
    member_id: int,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    """Remove (deactivate) a member. Cannot remove the last owner."""
    org, _ = org_ctx
    mem = db.query(OrganizationMember).filter(
        OrganizationMember.id == member_id,
        OrganizationMember.org_id == org.id,
    ).first()
    if not mem:
        raise HTTPException(status_code=404, detail="Member not found")

    if mem.role == "owner":
        owner_count = db.query(OrganizationMember).filter(
            OrganizationMember.org_id == org.id,
            OrganizationMember.role == "owner",
            OrganizationMember.is_active == True,
        ).count()
        if owner_count <= 1:
            raise HTTPException(status_code=400, detail="Cannot remove the last owner")

    uname = mem.user.username if mem.user else f"user#{mem.user_id}"
    mem.is_active = False
    db.commit()
    audit_log(db, org.id, current_user, "remove_member", entity_type="organization_member",
              entity_id=member_id, detail=f"Removed '{uname}' from org")
    return {"message": "Member removed"}


# ─── Org-Level Vendor Directory ───────────────────────────────────────────────

@router.get("/vendors")
def list_vendors(
    search: Optional[str] = None,
    trade: Optional[str] = None,
    org_ctx: Tuple = Depends(get_current_org),
    db: Session = Depends(get_db),
):
    """List all vendors for this org."""
    org, _ = org_ctx
    q = db.query(OrgVendor).filter(OrgVendor.org_id == org.id, OrgVendor.is_active == True)
    if search:
        q = q.filter(
            (OrgVendor.name.ilike(f"%{search}%")) |
            (OrgVendor.vendor_code.ilike(f"%{search}%")) |
            (OrgVendor.contact_name.ilike(f"%{search}%"))
        )
    if trade:
        q = q.filter(OrgVendor.trade.ilike(f"%{trade}%"))
    return q.order_by(OrgVendor.name).all()


@router.post("/vendors", response_model=OrgVendorOut)
def create_vendor(
    body: OrgVendorCreate,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin", "editor")),
    db: Session = Depends(get_db),
):
    """Create a new org-level vendor."""
    org, _ = org_ctx
    if body.vendor_code:
        existing = db.query(OrgVendor).filter(
            OrgVendor.org_id == org.id,
            OrgVendor.vendor_code == body.vendor_code,
        ).first()
        if existing:
            raise HTTPException(status_code=400, detail=f"Vendor code '{body.vendor_code}' already exists")

    v = OrgVendor(org_id=org.id, **body.model_dump())
    db.add(v)
    db.commit()
    db.refresh(v)
    return v


@router.put("/vendors/{vendor_id}", response_model=OrgVendorOut)
def update_vendor(
    vendor_id: int,
    body: OrgVendorCreate,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin", "editor")),
    db: Session = Depends(get_db),
):
    org, _ = org_ctx
    v = db.query(OrgVendor).filter(OrgVendor.id == vendor_id, OrgVendor.org_id == org.id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(v, field, value)
    db.commit()
    db.refresh(v)
    return v


@router.delete("/vendors/{vendor_id}")
def delete_vendor(
    vendor_id: int,
    org_ctx: Tuple = Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    org, _ = org_ctx
    v = db.query(OrgVendor).filter(OrgVendor.id == vendor_id, OrgVendor.org_id == org.id).first()
    if not v:
        raise HTTPException(status_code=404, detail="Vendor not found")
    v.is_active = False
    db.commit()
    return {"message": "Vendor deactivated"}


# ─── Super-Admin: all orgs ────────────────────────────────────────────────────

@router.get("/admin/all")
def superadmin_list_orgs(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Super-admin only: list all organizations with stats."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    orgs = db.query(Organization).order_by(Organization.created_at.desc()).all()
    result = []
    for org in orgs:
        data = {
            "id": org.id, "name": org.name, "slug": org.slug, "plan": org.plan,
            "is_active": org.is_active, "created_at": str(org.created_at),
        }
        data.update(_org_stats(org, db))
        result.append(data)
    return result


@router.post("/admin/create")
def superadmin_create_org(
    body: OrgCreate,
    owner_username: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Super-admin only: create an org and assign an owner."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Super-admin access required")

    existing = db.query(Organization).filter(Organization.slug == body.slug).first()
    if existing:
        raise HTTPException(status_code=400, detail="Slug already exists")

    owner = db.query(User).filter(User.username == owner_username).first()
    if not owner:
        raise HTTPException(status_code=404, detail=f"User '{owner_username}' not found")

    org = Organization(name=body.name, slug=body.slug)
    db.add(org)
    db.flush()
    mem = OrganizationMember(org_id=org.id, user_id=owner.id, role="owner", invited_by=current_user.id)
    db.add(mem)
    db.commit()
    db.refresh(org)
    return {"id": org.id, "name": org.name, "slug": org.slug, "owner": owner_username}


@router.put("/admin/{org_id}/toggle")
def superadmin_toggle_org(
    org_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Super-admin only: activate or suspend an org."""
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Super-admin access required")
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    org.is_active = not org.is_active
    db.commit()
    return {"id": org.id, "is_active": org.is_active}



# ── Email Invitations ─────────────────────────────────────────────────────────

@router.post("/invite")
def invite_member(
    body: dict,
    background_tasks: BackgroundTasks,
    org_ctx=Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Send an email invitation to join the org. Requires owner/admin."""
    org, _ = org_ctx
    email = (body.get("email") or "").strip().lower()
    role  = body.get("role", "editor")
    if not email:
        raise HTTPException(status_code=400, detail="email required")
    if role not in ROLES:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLES)}")

    # Already a member?
    existing_user = db.query(User).filter(User.email == email).first()
    if existing_user:
        mem = db.query(OrganizationMember).filter(
            OrganizationMember.org_id == org.id,
            OrganizationMember.user_id == existing_user.id,
            OrganizationMember.is_active == True,
        ).first()
        if mem:
            raise HTTPException(status_code=400, detail="This email is already a member of the org")

    # Invalidate existing pending invites to this email/org
    db.query(OrgInvitation).filter(
        OrgInvitation.org_id == org.id,
        OrgInvitation.email == email,
        OrgInvitation.accepted_at == None,
    ).delete()
    db.commit()

    token = secrets.token_urlsafe(32)
    db.add(OrgInvitation(
        org_id=org.id, email=email, role=role,
        token=token, invited_by=current_user.id,
        expires_at=datetime.utcnow() + timedelta(days=7),
    ))
    db.commit()

    from ..services.email import send_invite
    background_tasks.add_task(send_invite, email, org.name, current_user.username, role, token)
    return {"message": f"Invitation sent to {email}"}


@router.get("/invitations")
def list_invitations(
    org_ctx=Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    """List pending invitations for the current org."""
    org, _ = org_ctx
    invites = db.query(OrgInvitation).filter(
        OrgInvitation.org_id == org.id,
        OrgInvitation.accepted_at == None,
        OrgInvitation.expires_at > datetime.utcnow(),
    ).order_by(OrgInvitation.created_at.desc()).all()
    return [{"id": i.id, "email": i.email, "role": i.role,
             "expires_at": str(i.expires_at), "invited_by": i.inviter.username if i.inviter else ""}
            for i in invites]


@router.delete("/invitations/{invite_id}")
def cancel_invitation(
    invite_id: int,
    org_ctx=Depends(require_org_role("owner", "admin")),
    db: Session = Depends(get_db),
):
    """Cancel a pending invitation."""
    org, _ = org_ctx
    inv = db.query(OrgInvitation).filter(
        OrgInvitation.id == invite_id,
        OrgInvitation.org_id == org.id,
    ).first()
    if not inv:
        raise HTTPException(status_code=404, detail="Invitation not found")
    db.delete(inv)
    db.commit()
    return {"message": "Invitation cancelled"}
