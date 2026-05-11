"""Subcontract Agreement Generator — convert bid to subcontract with e-signature."""
import secrets
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.orm import Session

from ..database import SessionLocal, get_db
from ..dependencies import get_current_user, require_org_member, FINANCE_READ_ROLES, FINANCE_WRITE_ROLES
from ..models import SubcontractAgreement, Project, BidResponse

router = APIRouter(prefix="/api/project", tags=["subcontract"])
_public_router = APIRouter(tags=["subcontract-public"])


def _db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _proj(project_id, user, db):
    p = db.query(Project).filter(Project.id == project_id).first()
    if not p: raise HTTPException(404)
    require_org_member(db, p.org_id, user.id, FINANCE_READ_ROLES)
    return p


# ── CRUD ───────────────────────────────────────────────────────────────────────

@router.get("/{project_id}/subcontracts")
def list_subcontracts(project_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    _proj(project_id, user, db)
    rows = db.query(SubcontractAgreement).filter(SubcontractAgreement.project_id == project_id).order_by(SubcontractAgreement.created_at.desc()).all()
    return [_out(r) for r in rows]


def _out(r):
    return {
        "id": r.id, "vendor_name": r.vendor_name, "trade": r.trade,
        "contract_number": r.contract_number, "contract_amount": r.contract_amount,
        "holdback_pct": r.holdback_pct, "payment_terms": r.payment_terms,
        "start_date": r.start_date, "end_date": r.end_date,
        "status": r.status, "signed_at": r.signed_at.isoformat() if r.signed_at else None,
        "signed_by_name": r.signed_by_name,
        "sign_url": f"/subcontract/{r.sign_token}" if r.sign_token and r.status != "executed" else None,
        "created_at": r.created_at.isoformat(),
    }


@router.post("/{project_id}/subcontracts")
def create_subcontract(project_id: int, body: dict, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    # Auto-number
    last = db.query(SubcontractAgreement).filter(SubcontractAgreement.project_id == project_id).order_by(SubcontractAgreement.id.desc()).first()
    num = f"SC-{((int(last.contract_number.split('-')[1]) if last and last.contract_number else 0) + 1):03d}"
    s = SubcontractAgreement(
        org_id=p.org_id, project_id=project_id,
        bid_response_id=body.get("bid_response_id"),
        vendor_id=body.get("vendor_id"),
        vendor_name=body["vendor_name"],
        trade=body.get("trade"),
        contract_number=body.get("contract_number", num),
        scope_of_work=body.get("scope_of_work"),
        inclusions=body.get("inclusions"),
        exclusions=body.get("exclusions"),
        contract_amount=body["contract_amount"],
        holdback_pct=body.get("holdback_pct", 10.0),
        payment_terms=body.get("payment_terms", "Net 30 — progress draws"),
        start_date=body.get("start_date"),
        end_date=body.get("end_date"),
        insurance_required=body.get("insurance_required", True),
        bond_required=body.get("bond_required", False),
        warranty_period=body.get("warranty_period", "1 year from Substantial Performance"),
        dispute_resolution=body.get("dispute_resolution", "CCDC"),
        governing_law=body.get("governing_law", p.province or "ON"),
        status="draft",
        sign_token=secrets.token_urlsafe(24),
        notes=body.get("notes"),
        created_by=user.id,
    )
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "contract_number": s.contract_number, "sign_url": f"/subcontract/{s.sign_token}", "ok": True}


@router.post("/{project_id}/subcontracts/from-bid/{response_id}")
def create_from_bid(project_id: int, response_id: int, body: dict,
                    db: Session = Depends(_db), user=Depends(get_current_user)):
    """Create subcontract pre-populated from an awarded bid response."""
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    bid = db.query(BidResponse).filter(BidResponse.id == response_id, BidResponse.project_id == project_id).first()
    if not bid: raise HTTPException(404, "Bid response not found")
    last = db.query(SubcontractAgreement).filter(SubcontractAgreement.project_id == project_id).order_by(SubcontractAgreement.id.desc()).first()
    num = f"SC-{((int(last.contract_number.split('-')[1]) if last and last.contract_number else 0) + 1):03d}"
    pkg = bid.package
    s = SubcontractAgreement(
        org_id=p.org_id, project_id=project_id,
        bid_response_id=response_id,
        vendor_name=bid.vendor_name,
        trade=pkg.trade_category if pkg else None,
        contract_number=num,
        scope_of_work=pkg.description if pkg else None,
        inclusions=bid.inclusions,
        exclusions=bid.exclusions,
        contract_amount=bid.total_amount or 0,
        holdback_pct=body.get("holdback_pct", 10.0),
        payment_terms=body.get("payment_terms", "Net 30 — progress draws"),
        start_date=body.get("start_date"),
        end_date=body.get("end_date"),
        insurance_required=True,
        bond_required=body.get("bond_required", False),
        warranty_period="1 year from Substantial Performance",
        dispute_resolution="CCDC",
        governing_law=p.province or "ON",
        status="draft",
        sign_token=secrets.token_urlsafe(24),
        created_by=user.id,
    )
    db.add(s); db.commit(); db.refresh(s)
    return {"id": s.id, "contract_number": s.contract_number, "sign_url": f"/subcontract/{s.sign_token}", "ok": True}


@router.put("/{project_id}/subcontracts/{sc_id}")
def update_subcontract(project_id: int, sc_id: int, body: dict,
                       db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    s = db.query(SubcontractAgreement).filter(SubcontractAgreement.id == sc_id, SubcontractAgreement.project_id == project_id).first()
    if not s: raise HTTPException(404)
    for f in ["vendor_name","trade","scope_of_work","inclusions","exclusions","contract_amount","holdback_pct","payment_terms","start_date","end_date","insurance_required","bond_required","warranty_period","dispute_resolution","governing_law","status","notes"]:
        if f in body: setattr(s, f, body[f])
    db.commit()
    return {"ok": True}


@router.delete("/{project_id}/subcontracts/{sc_id}")
def delete_subcontract(project_id: int, sc_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    p = _proj(project_id, user, db)
    require_org_member(db, p.org_id, user.id, FINANCE_WRITE_ROLES)
    s = db.query(SubcontractAgreement).filter(SubcontractAgreement.id == sc_id, SubcontractAgreement.project_id == project_id).first()
    if s: db.delete(s); db.commit()
    return {"ok": True}


@router.get("/{project_id}/subcontracts/{sc_id}/html")
def preview_subcontract(project_id: int, sc_id: int, db: Session = Depends(_db), user=Depends(get_current_user)):
    """Return HTML preview of the subcontract for printing."""
    p = _proj(project_id, user, db)
    s = db.query(SubcontractAgreement).filter(SubcontractAgreement.id == sc_id, SubcontractAgreement.project_id == project_id).first()
    if not s: raise HTTPException(404)
    return {"html": _build_subcontract_html(s, p)}


# ── Public E-Signature Portal ──────────────────────────────────────────────────

@_public_router.get("/subcontract/{token}", response_class=HTMLResponse)
def subcontract_sign_page(token: str, db: Session = Depends(get_db)):
    s = db.query(SubcontractAgreement).filter(SubcontractAgreement.sign_token == token).first()
    if not s: return HTMLResponse("<html><body><h2>Agreement not found.</h2></body></html>", 404)
    p = db.query(Project).filter(Project.id == s.project_id).first()

    status_html = ""
    if s.signed_at:
        status_html = f'<div class="bg-green-50 border border-green-200 rounded-xl p-5 text-center"><i class="fa-solid fa-signature text-3xl text-green-500 mb-2"></i><p class="font-bold text-green-700">Executed by {s.signed_by_name} on {s.signed_at.strftime("%B %d, %Y")}</p></div>'
    sign_section = "" if s.signed_at else """
    <div class="bg-gray-50 border rounded-xl p-5 mt-6">
      <h3 class="font-bold text-gray-800 mb-4">Electronic Signature</h3>
      <div class="space-y-3">
        <div><label class="block text-xs font-medium text-gray-600 mb-1">Full Legal Name *</label><input id="signName" type="text" class="w-full border rounded-xl px-3 py-2 text-sm" /></div>
        <div><label class="block text-xs font-medium text-gray-600 mb-1">Title / Position *</label><input id="signTitle" type="text" class="w-full border rounded-xl px-3 py-2 text-sm" /></div>
        <div><label class="block text-xs font-medium text-gray-600 mb-1">Company *</label><input id="signCompany" type="text" class="w-full border rounded-xl px-3 py-2 text-sm" /></div>
        <div><label class="block text-xs font-medium text-gray-600 mb-1">Date</label><input id="signDate" type="date" class="w-full border rounded-xl px-3 py-2 text-sm" /></div>
        <p class="text-xs text-gray-500">By clicking "Execute Agreement" you agree that this electronic signature constitutes your legal signature on this subcontract agreement.</p>
        <button onclick="signAgreement()" class="w-full py-3 bg-blue-600 text-white rounded-xl font-bold hover:bg-blue-700">Execute Agreement</button>
        <div id="signError" class="hidden text-red-600 text-sm text-center"></div>
      </div>
    </div>
    <script>
    async function signAgreement(){
      const name=document.getElementById('signName').value.trim();
      const title=document.getElementById('signTitle').value.trim();
      if(!name||!title){document.getElementById('signError').textContent='Name and title required';document.getElementById('signError').classList.remove('hidden');return;}
      const r=await fetch(window.location.pathname+'/sign',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({signed_by_name:name+' ('+title+')'})});
      if(r.ok){location.reload();}else{const e=await r.json();document.getElementById('signError').textContent=e.detail||'Error';document.getElementById('signError').classList.remove('hidden');}
    }
    </script>"""

    contract_html = _build_subcontract_html(s, p)
    return HTMLResponse(f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"/><meta name="viewport" content="width=device-width,initial-scale=1.0"/>
<title>Subcontract Agreement — {s.contract_number}</title>
<link rel="stylesheet" href="/static/css/fontawesome/all.min.css"/>
<script src="/static/js/tailwind.min.js"></script>
</head><body class="bg-gray-50 font-sans">
<div class="max-w-3xl mx-auto px-4 py-8">
  <div class="text-center mb-6"><img src="/static/favicon.svg" class="w-10 h-10 mx-auto rounded-xl mb-2" alt="Finel AI"/><h1 class="text-2xl font-bold text-gray-800">Subcontract Agreement</h1><p class="text-gray-500">{p.name if p else ''}</p></div>
  {status_html}
  <div class="bg-white border rounded-2xl p-6 mt-4 prose max-w-none text-sm">{contract_html}</div>
  {sign_section}
  <p class="text-center text-xs text-gray-400 mt-6">Powered by <a href="https://projects.finel.ai" class="text-blue-500">Finel AI Projects</a></p>
</div></body></html>""")


@_public_router.post("/subcontract/{token}/sign")
def sign_subcontract(token: str, body: dict, db: Session = Depends(get_db)):
    from fastapi import Request
    s = db.query(SubcontractAgreement).filter(SubcontractAgreement.sign_token == token).first()
    if not s: raise HTTPException(404)
    if s.signed_at: raise HTTPException(400, "Already executed.")
    s.signed_at = datetime.utcnow()
    s.signed_by_name = body.get("signed_by_name", "")
    s.status = "executed"
    db.commit()
    return {"ok": True}


def _build_subcontract_html(s: SubcontractAgreement, p) -> str:
    """Generate HTML subcontract document from model data."""
    today = datetime.utcnow().strftime("%B %d, %Y")
    return f"""
<h2 style="text-align:center;font-size:18px;margin-bottom:4px">SUBCONTRACT AGREEMENT</h2>
<p style="text-align:center;color:#666;font-size:13px">{s.contract_number} · {today}</p>
<hr style="margin:12px 0"/>
<p><strong>Project:</strong> {p.name if p else '—'}<br/>
<strong>Owner/GC:</strong> {p.client or '—'}<br/>
<strong>Address:</strong> {p.address or '—'}<br/>
<strong>Subcontractor:</strong> {s.vendor_name}<br/>
<strong>Trade:</strong> {s.trade or '—'}</p>

<h3>1. SCOPE OF WORK</h3>
<p>{s.scope_of_work or 'As described in contract documents.'}</p>
{f'<p><strong>Inclusions:</strong> {s.inclusions}</p>' if s.inclusions else ''}
{f'<p><strong>Exclusions:</strong> {s.exclusions}</p>' if s.exclusions else ''}

<h3>2. CONTRACT AMOUNT</h3>
<p>The Subcontractor shall perform the Work for the sum of <strong>${s.contract_amount:,.2f} CAD</strong> (plus applicable HST/GST).</p>

<h3>3. HOLDBACK</h3>
<p>A statutory holdback of <strong>{s.holdback_pct:.0f}%</strong> shall be retained from each progress payment in accordance with the applicable provincial Construction Act.</p>

<h3>4. PAYMENT TERMS</h3>
<p>{s.payment_terms or 'Net 30 days from invoice date. Progress draws submitted monthly.'}</p>

<h3>5. SCHEDULE</h3>
<p>Work to commence: <strong>{s.start_date or 'As directed'}</strong><br/>
Substantial performance: <strong>{s.end_date or 'Per project schedule'}</strong></p>

<h3>6. INSURANCE</h3>
<p>{'Subcontractor shall maintain Commercial General Liability insurance of not less than $5,000,000 per occurrence and in the aggregate, and provide evidence thereof prior to commencing Work.' if s.insurance_required else 'Insurance requirements as per contract documents.'}</p>

<h3>7. BONDS</h3>
<p>{'Performance Bond and Labour & Material Payment Bond each in the amount of 50% of the Subcontract Price shall be provided prior to commencement.' if s.bond_required else 'No performance bond required.'}</p>

<h3>8. WARRANTY</h3>
<p>Subcontractor warrants its Work against defects for a period of <strong>{s.warranty_period or '1 year from Substantial Performance'}</strong>.</p>

<h3>9. DISPUTE RESOLUTION</h3>
<p>Disputes shall be resolved in accordance with {s.dispute_resolution or 'CCDC 2'} procedures. This Agreement is governed by the laws of the Province of {s.governing_law or 'Ontario'}.</p>

<h3>10. CCDC COMPLIANCE</h3>
<p>This Subcontract is subject to the requirements of the Ontario Construction Act (or applicable provincial legislation) including holdback, prompt payment, and lien rights provisions.</p>

<hr style="margin:20px 0"/>
<p style="font-size:11px;color:#888">This agreement, when executed electronically, constitutes a legally binding contract between the parties.</p>
"""
