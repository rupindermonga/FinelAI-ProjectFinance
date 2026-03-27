"""Full dynamic security & QA audit v2 — auth, IDOR, draws, claims, FX, payroll, cost tracking, bulk approve, filters, validation."""
import requests
import time
import os

BASE = os.getenv("TEST_BASE_URL", "http://localhost:8000")
RESULTS = []


def test(name, condition, detail=""):
    status = "PASS" if condition else "FAIL"
    RESULTS.append((status, name, detail))
    mark = "+" if condition else "X"
    line = f"  [{mark}] {name}"
    if detail and not condition:
        line += f" -- {detail}"
    print(line)


def login(username="admin", password=None):
    if password is None:
        password = os.getenv("ADMIN_PASSWORD", "Admin@2026!")
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    return r.json().get("access_token") if r.status_code == 200 else None


def auth(token):
    return {"Authorization": f"Bearer {token}"}


print("=" * 70)
print("FULL DYNAMIC SECURITY & QA AUDIT v2")
print("=" * 70)

# ── WAIT FOR RATE LIMITER TO CLEAR ───────────────────────────────────────
print("\n-- PRE-CHECK: waiting for rate limiter to clear --")
for attempt in range(24):  # max 2 min wait (24 * 5s)
    r = requests.post(f"{BASE}/api/auth/login", json={"username": "probe_limiter_check", "password": "x"})
    if r.status_code == 401:
        print(f"  Rate limiter clear (attempt {attempt + 1})")
        break
    if r.status_code == 429:
        if attempt == 0:
            print(f"  Rate limiter active, waiting up to 2 min for it to clear...")
        time.sleep(5)
else:
    print("  WARNING: Rate limiter did not clear after 2 min. Tests may fail.")

# ── AUTH ─────────────────────────────────────────────────────────────────
print("\n-- AUTH & INPUT VALIDATION --")
r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "admin123"})
test("Default admin123 rejected", r.status_code == 401)

token = login()
test("Admin login succeeds", token is not None)

r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "wrong"})
test("Wrong password = 401", r.status_code == 401)

r = requests.get(f"{BASE}/api/invoices")
test("No-auth = 401", r.status_code == 401)

r = requests.get(f"{BASE}/api/invoices", headers={"Authorization": "Bearer garbage"})
test("Garbage JWT = 401", r.status_code == 401)

ts = str(int(time.time()))

# Public registration should be disabled
r = requests.post(f"{BASE}/api/auth/register", json={"username": f"qa_{ts}", "email": f"qa_{ts}@example.com", "password": "StrongP@ss1"})
test("Public registration disabled (403)", r.status_code == 403)

# ── ADMIN USER MANAGEMENT ───────────────────────────────────────────────
print("\n-- ADMIN USER MANAGEMENT --")
# Admin creates user2
r = requests.post(f"{BASE}/api/admin/users", headers=auth(token), json={"username": f"qa_{ts}", "email": f"qa_{ts}@example.com", "password": "StrongP@ss1"})
test("Admin creates user", r.status_code == 200)

user2_token = login(f"qa_{ts}", "StrongP@ss1")
test("User2 login", user2_token is not None)
if not user2_token:
    print("  WARNING: User2 auth failed. Cross-user tests will use a dummy token.")
    user2_token = "dummy_invalid_token"

# Admin can list users
r = requests.get(f"{BASE}/api/admin/users", headers=auth(token))
test("Admin lists users", r.status_code == 200 and len(r.json()) > 0)

# Non-admin cant list users
r = requests.get(f"{BASE}/api/admin/users", headers=auth(user2_token))
test("Non-admin cant list users", r.status_code == 403)

# Admin create validation
r = requests.post(f"{BASE}/api/admin/users", headers=auth(token), json={"username": "ab", "email": "x@x.com", "password": "Test1234!"})
test("Short username rejected", r.status_code == 400)
r = requests.post(f"{BASE}/api/admin/users", headers=auth(token), json={"username": f"v_{ts}", "email": f"v_{ts}@x.com", "password": "abc"})
test("Short password rejected", r.status_code == 400)
r = requests.post(f"{BASE}/api/admin/users", headers=auth(token), json={"username": f"qa_{ts}", "email": f"dup_{ts}@x.com", "password": "Test1234!"})
test("Duplicate username rejected", r.status_code == 400)

# Change password
r = requests.put(f"{BASE}/api/auth/change-password", headers=auth(user2_token), json={"current_password": "StrongP@ss1", "new_password": "NewPass99!"})
test("User changes own password", r.status_code == 200)
r = requests.post(f"{BASE}/api/auth/login", json={"username": f"qa_{ts}", "password": "NewPass99!"})
test("Login with new password", r.status_code == 200)
user2_token = r.json()["access_token"]

# Wrong current password
r = requests.put(f"{BASE}/api/auth/change-password", headers=auth(user2_token), json={"current_password": "wrong", "new_password": "X1234567!"})
test("Wrong current password rejected", r.status_code == 401)

# Admin reset password
users_list = requests.get(f"{BASE}/api/admin/users", headers=auth(token)).json()
u2_entry = next((u for u in users_list if u["username"] == f"qa_{ts}"), None)
if u2_entry:
    r = requests.put(f"{BASE}/api/admin/users/{u2_entry['id']}/reset-password", headers=auth(token), json={"password": "ResetPw99!"})
    test("Admin resets user password", r.status_code == 200)
    r = requests.post(f"{BASE}/api/auth/login", json={"username": f"qa_{ts}", "password": "ResetPw99!"})
    test("Login with reset password", r.status_code == 200)
    user2_token = r.json()["access_token"]

# Toggle active
if u2_entry:
    r = requests.put(f"{BASE}/api/admin/users/{u2_entry['id']}/toggle-active", headers=auth(token))
    test("Toggle user inactive", r.status_code == 200 and r.json()["is_active"] == False)
    r = requests.post(f"{BASE}/api/auth/login", json={"username": f"qa_{ts}", "password": "ResetPw99!"})
    test("Inactive user cant login", r.status_code == 403)
    # Reactivate
    requests.put(f"{BASE}/api/admin/users/{u2_entry['id']}/toggle-active", headers=auth(token))
    user2_token = login(f"qa_{ts}", "ResetPw99!")

# ── SECURITY HEADERS ────────────────────────────────────────────────────
print("\n-- SECURITY HEADERS --")
r = requests.get(f"{BASE}/")
test("CSP header", "content-security-policy" in r.headers)
test("X-Content-Type-Options: nosniff", r.headers.get("x-content-type-options") == "nosniff")
test("X-Frame-Options: DENY", r.headers.get("x-frame-options") == "DENY")

r = requests.options(f"{BASE}/api/invoices", headers={"Origin": "https://evil.com", "Access-Control-Request-Method": "GET"})
acao = r.headers.get("access-control-allow-origin", "")
test("CORS blocks evil origin", acao != "https://evil.com" and acao != "*")

# ── DOCS DISABLED ───────────────────────────────────────────────────────
print("\n-- DOCS EXPOSURE --")
r = requests.get(f"{BASE}/docs")
test("/docs not Swagger", r.status_code == 404 or (r.status_code == 200 and "swagger" not in r.text.lower()))
r = requests.get(f"{BASE}/openapi.json")
test("/openapi.json not schema", r.status_code == 404 or (r.status_code == 200 and "paths" not in r.text))

# ── EXPORT AUTH ─────────────────────────────────────────────────────────
print("\n-- EXPORT AUTH --")
r = requests.get(f"{BASE}/api/export/excel")
test("Export no-auth = 401", r.status_code == 401)
r = requests.get(f"{BASE}/api/export/json?token={token}")
test("Export ?token= rejected", r.status_code == 401)
r = requests.get(f"{BASE}/api/export/excel", headers=auth(token))
test("Export with Bearer works", r.status_code == 200)

# ── UPLOAD VALIDATION ───────────────────────────────────────────────────
print("\n-- UPLOAD VALIDATION --")
r = requests.post(f"{BASE}/api/upload", headers=auth(token), files={"files": ("fake.pdf", b"not a pdf", "application/pdf")})
test("Fake PDF rejected", r.status_code == 200 and any(x.get("status") == "rejected" for x in r.json().get("results", [])))

# ── SSE AUTH ────────────────────────────────────────────────────────────
print("\n-- SSE AUTH --")
r = requests.get(f"{BASE}/api/invoices/stream", stream=True, timeout=3)
test("SSE no token = 401", r.status_code == 401)
r = requests.get(f"{BASE}/api/invoices/stream?token={token}", stream=True, timeout=3)
test("SSE main JWT rejected (scope)", r.status_code == 401)
r.close()
r = requests.post(f"{BASE}/api/invoices/sse-token", headers=auth(token))
test("SSE token endpoint works", r.status_code == 200)
if r.status_code == 200:
    sse_tok = r.json()["sse_token"]
    r2 = requests.get(f"{BASE}/api/invoices/stream?token={sse_tok}", stream=True, timeout=3)
    test("SSE with SSE token works", r2.status_code == 200)
    r2.close()

# ── IDOR / CROSS-USER ───────────────────────────────────────────────────
print("\n-- IDOR / CROSS-USER ISOLATION --")
admin_invs = requests.get(f"{BASE}/api/invoices", headers=auth(token)).json().get("items", [])
user2_invs = requests.get(f"{BASE}/api/invoices", headers=auth(user2_token)).json().get("items", [])
test("User2 sees 0 invoices", len(user2_invs) == 0)

r_admin_cols = requests.get(f"{BASE}/api/columns", headers=auth(token))
admin_cols = r_admin_cols.json() if r_admin_cols.status_code == 200 and isinstance(r_admin_cols.json(), list) else []
r_u2_cols = requests.get(f"{BASE}/api/columns", headers=auth(user2_token))
user2_cols = r_u2_cols.json() if r_u2_cols.status_code == 200 and isinstance(r_u2_cols.json(), list) else []
test("Column IDs user-scoped", len(admin_cols) == 0 or len(user2_cols) == 0 or {c["id"] for c in admin_cols}.isdisjoint({c["id"] for c in user2_cols}))

if admin_cols and isinstance(admin_cols, list):
    r = requests.put(f"{BASE}/api/columns/{admin_cols[0]['id']}", headers=auth(user2_token), json={"field_label": "HACKED"})
    test("User2 cant modify admin column", r.status_code in (403, 404))

r = requests.get(f"{BASE}/api/admin/api-keys", headers=auth(user2_token))
test("Non-admin blocked from API keys", r.status_code == 403)

# ── PROJECT FINANCE ─────────────────────────────────────────────────────
print("\n-- PROJECT FINANCE --")
r = requests.get(f"{BASE}/api/project/dashboard", headers=auth(token))
test("Dashboard loads", r.status_code == 200 and r.json().get("project") is not None)
dash = r.json()
test("5 cost categories", len(dash.get("categories", [])) == 5)
test("Cost tracking in dashboard", "cost_tracking" in dash)
ct = dash.get("cost_tracking", {})
test("Cost tracking has committed", "committed" in ct)
test("Cost tracking has lender", "lender" in ct)
test("Cost tracking has govt", "govt" in ct)
test("Cost tracking has net_position", "net_position" in ct)
test("Cost tracking has payroll_committed", "payroll_committed" in ct)

cats = requests.get(f"{BASE}/api/project/categories", headers=auth(token)).json()
if cats:
    r = requests.put(f"{BASE}/api/project/categories/{cats[0]['id']}", headers=auth(token), json={"budget": -100})
    test("Negative budget rejected", r.status_code == 400)

# ── DRAWS ────────────────────────────────────────────────────────────────
print("\n-- DRAWS --")
for d in requests.get(f"{BASE}/api/project/draws", headers=auth(token)).json():
    requests.delete(f"{BASE}/api/project/draws/{d['id']}", headers=auth(token))

r = requests.post(f"{BASE}/api/project/draws", headers=auth(token), json={"draw_number": 99, "fx_rate": 1.38})
test("Create Draw 99", r.status_code == 200)
draw_id = r.json()["id"]

r = requests.post(f"{BASE}/api/project/draws", headers=auth(token), json={"draw_number": 99, "fx_rate": 1.40})
test("Duplicate draw rejected", r.status_code == 400)

r = requests.put(f"{BASE}/api/project/draws/{draw_id}", headers=auth(user2_token), json={"fx_rate": 999})
test("User2 cant update admin draw", r.status_code == 404)

# ── CLAIMS (DUAL FK) ────────────────────────────────────────────────────
print("\n-- CLAIMS (DUAL FK) --")
for c in requests.get(f"{BASE}/api/project/claims", headers=auth(token)).json():
    requests.delete(f"{BASE}/api/project/claims/{c['id']}", headers=auth(token))

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 99, "claim_type": "provincial", "fx_rate": 1.35})
test("Create provincial claim", r.status_code == 200)
prov_id = r.json()["id"]

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 99, "claim_type": "federal", "fx_rate": 1.36})
test("Create federal claim", r.status_code == 200)
fed_id = r.json()["id"]

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 2, "claim_type": "municipal", "fx_rate": 1.0})
test("Invalid claim_type rejected", r.status_code == 400)

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 99, "claim_type": "provincial", "fx_rate": 1.0})
test("Duplicate provincial claim rejected", r.status_code == 400)

# Assign invoice to both claims independently
processed = [i for i in admin_invs if i["status"] == "processed"]
if processed:
    inv_ids = [processed[0]["id"]]
    r = requests.put(f"{BASE}/api/project/draws/{draw_id}/invoices", headers=auth(token), json=inv_ids)
    test("Assign invoice to draw", r.status_code == 200)
    r = requests.put(f"{BASE}/api/project/claims/{prov_id}/invoices", headers=auth(token), json=inv_ids)
    test("Assign to prov claim", r.status_code == 200)
    r = requests.put(f"{BASE}/api/project/claims/{fed_id}/invoices", headers=auth(token), json=inv_ids)
    test("Assign to fed claim", r.status_code == 200)

    # Verify dual assignment
    inv_detail = requests.get(f"{BASE}/api/invoices", headers=auth(token)).json()["items"]
    inv = next((i for i in inv_detail if i["id"] == processed[0]["id"]), None)
    if inv:
        test("Invoice has draw_id", inv.get("draw_id") == draw_id)
        test("Invoice has provincial_claim_id", inv.get("provincial_claim_id") == prov_id)
        test("Invoice has federal_claim_id", inv.get("federal_claim_id") == fed_id)

# User2 IDOR on claims
r = requests.put(f"{BASE}/api/project/claims/{prov_id}", headers=auth(user2_token), json={"fx_rate": 999})
test("User2 cant update admin claim", r.status_code == 404)

# ── BULK APPROVE ─────────────────────────────────────────────────────────
print("\n-- BULK APPROVE --")
if processed:
    # Bulk approve draw
    r = requests.post(f"{BASE}/api/project/draws/{draw_id}/approve-all", headers=auth(token), json={})
    test("Bulk approve draw", r.status_code == 200 and r.json()["count"] >= 1)

    # Verify invoice is now approved
    invs_after = requests.get(f"{BASE}/api/invoices", headers=auth(token)).json()["items"]
    inv_after = next((i for i in invs_after if i["id"] == processed[0]["id"]), None)
    if inv_after:
        test("Invoice lender_status = approved", inv_after.get("lender_status") == "approved")
        test("Invoice lender_approved_amt set", (inv_after.get("lender_approved_amt") or 0) > 0)

    # Bulk approve claim
    r = requests.post(f"{BASE}/api/project/claims/{prov_id}/approve-all", headers=auth(token), json={})
    test("Bulk approve prov claim", r.status_code == 200 and r.json()["count"] >= 1)

    invs_after2 = requests.get(f"{BASE}/api/invoices", headers=auth(token)).json()["items"]
    inv_after2 = next((i for i in invs_after2 if i["id"] == processed[0]["id"]), None)
    if inv_after2:
        test("Invoice govt_status = approved", inv_after2.get("govt_status") == "approved")
        test("Invoice govt_approved_amt set", (inv_after2.get("govt_approved_amt") or 0) > 0)

    # User2 cant bulk approve admin draw
    r = requests.post(f"{BASE}/api/project/draws/{draw_id}/approve-all", headers=auth(user2_token), json={})
    test("User2 cant bulk approve admin draw", r.status_code == 404)

    r = requests.post(f"{BASE}/api/project/claims/{prov_id}/approve-all", headers=auth(user2_token), json={})
    test("User2 cant bulk approve admin claim", r.status_code == 404)

# ── INVOICE FILTERS (draw_id, claim_id) ──────────────────────────────────
print("\n-- INVOICE FILTERS --")
if processed:
    # Filter by draw
    r = requests.get(f"{BASE}/api/invoices?draw_id={draw_id}", headers=auth(token))
    test("Filter by draw_id", r.status_code == 200 and r.json()["total"] >= 1)

    # Filter by unassigned draw
    r = requests.get(f"{BASE}/api/invoices?draw_id=none", headers=auth(token))
    test("Filter unassigned draw", r.status_code == 200)

    # Filter by claim
    r = requests.get(f"{BASE}/api/invoices?claim_id={prov_id}", headers=auth(token))
    test("Filter by claim_id (prov)", r.status_code == 200 and r.json()["total"] >= 1)

    r = requests.get(f"{BASE}/api/invoices?claim_id={fed_id}", headers=auth(token))
    test("Filter by claim_id (fed)", r.status_code == 200 and r.json()["total"] >= 1)

    r = requests.get(f"{BASE}/api/invoices?claim_id=none", headers=auth(token))
    test("Filter unassigned claim", r.status_code == 200)

# ── COPY DRAW TO CLAIM ──────────────────────────────────────────────────
print("\n-- COPY DRAW TO CLAIM --")
if processed:
    r2 = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 100, "claim_type": "federal", "fx_rate": 1.37})
    if r2.status_code == 200:
        copy_id = r2.json()["id"]
        r = requests.put(f"{BASE}/api/project/claims/{copy_id}/copy-from-draw/{draw_id}", headers=auth(token), json={})
        test("Copy draw to claim", r.status_code == 200 and r.json()["invoice_count"] >= 1)

# ── FX RATE ──────────────────────────────────────────────────────────────
print("\n-- FX RATE --")
r = requests.get(f"{BASE}/api/project/fx-rate")
test("FX rate endpoint", r.status_code == 200 and r.json().get("rate", 0) > 1.0)

# ── PAYROLL ──────────────────────────────────────────────────────────────
print("\n-- PAYROLL --")
# Negative payroll rejected
r = requests.post(f"{BASE}/api/project/payroll", headers=auth(token), json={"gross_pay": -100, "working_days": 10})
test("Negative payroll rejected", r.status_code == 400)

# Valid payroll
r = requests.post(f"{BASE}/api/project/payroll", headers=auth(token), json={
    "employee_name": "QA Tester", "company_name": "TestCorp",
    "pay_period_start": "2026-03-01", "pay_period_end": "2026-03-15",
    "gross_pay": 4000, "cpp": 200, "ei": 80, "insurance": 50, "holiday_pay": 160,
    "working_days": 24, "statutory_holidays": 2, "province": "ON"
})
test("Create payroll entry", r.status_code == 200)
if r.status_code == 200:
    p = r.json()
    pay_id = p["id"]
    test("Eligible days = 22", p["eligible_days"] == 22)
    test("Daily rate = 181.82", abs(p["daily_rate"] - 181.82) < 0.01)
    test("Lender billable = gross", p["lender_billable"] == 4000.0)
    test("Govt billable excludes CPP/EI/Ins/Holiday", p["govt_billable"] == 3510.0)

    # Negative CPP update rejected
    r = requests.put(f"{BASE}/api/project/payroll/{pay_id}", headers=auth(token), json={"cpp": -50})
    test("Negative CPP update rejected", r.status_code == 400)

    # User2 cant access
    r = requests.put(f"{BASE}/api/project/payroll/{pay_id}", headers=auth(user2_token), json={"gross_pay": 999})
    test("User2 cant update admin payroll", r.status_code == 404)

    r = requests.delete(f"{BASE}/api/project/payroll/{pay_id}", headers=auth(user2_token))
    test("User2 cant delete admin payroll", r.status_code == 404)

    # Cleanup
    requests.delete(f"{BASE}/api/project/payroll/{pay_id}", headers=auth(token))

# ── INVOICE COST UPDATE ─────────────────────────────────────────────────
print("\n-- INVOICE COST UPDATE --")
if processed:
    inv = processed[0]
    r = requests.put(f"{BASE}/api/project/invoices/{inv['id']}/cost", headers=auth(token), json={
        "lender_margin_pct": 30, "govt_margin_pct": 10
    })
    test("Update invoice cost", r.status_code == 200)

    invs_check = requests.get(f"{BASE}/api/invoices", headers=auth(token)).json()["items"]
    inv_check = next((i for i in invs_check if i["id"] == inv["id"]), None)
    if inv_check:
        test("Lender margin amt calculated", (inv_check.get("lender_margin_amt") or 0) > 0)
        test("Govt margin amt calculated", (inv_check.get("govt_margin_amt") or 0) > 0)

    # User2 cant update admin invoice cost
    r = requests.put(f"{BASE}/api/project/invoices/{inv['id']}/cost", headers=auth(user2_token), json={"lender_margin_pct": 999})
    test("User2 cant update admin invoice cost", r.status_code == 404)

# ── PAYMENT VALIDATION ──────────────────────────────────────────────────
print("\n-- PAYMENT VALIDATION --")
if processed:
    r = requests.post(f"{BASE}/api/project/payments", headers=auth(token), json={"invoice_id": processed[0]["id"], "amount": -50, "payment_date": "2026-03-26"})
    test("Negative payment rejected", r.status_code == 400)
    r = requests.post(f"{BASE}/api/project/payments", headers=auth(user2_token), json={"invoice_id": processed[0]["id"], "amount": 1, "payment_date": "2026-03-26"})
    test("User2 cant pay admin invoice", r.status_code == 404)

# ── ALLOCATION VALIDATION ───────────────────────────────────────────────
print("\n-- ALLOCATION VALIDATION --")
if processed and cats:
    r = requests.put(f"{BASE}/api/project/allocations/{processed[0]['id']}", headers=auth(token), json=[{"invoice_id": processed[0]["id"], "category_id": cats[0]["id"], "percentage": -10}])
    test("Negative allocation rejected", r.status_code == 400)
    r = requests.put(f"{BASE}/api/project/allocations/{processed[0]['id']}", headers=auth(token), json=[
        {"invoice_id": processed[0]["id"], "category_id": cats[0]["id"], "percentage": 60},
        {"invoice_id": processed[0]["id"], "category_id": cats[1]["id"], "percentage": 60},
    ])
    test("Allocation >100% rejected", r.status_code == 400)
    r = requests.put(f"{BASE}/api/project/allocations/{processed[0]['id']}", headers=auth(user2_token), json=[])
    test("User2 cant allocate admin invoice", r.status_code == 404)

# ── CROSS-USER PROJECT ──────────────────────────────────────────────────
print("\n-- CROSS-USER PROJECT --")
u2_dash = requests.get(f"{BASE}/api/project/dashboard", headers=auth(user2_token)).json()
test("User2 has own project", u2_dash.get("project") is not None)
test("User2 payroll empty", len(requests.get(f"{BASE}/api/project/payroll", headers=auth(user2_token)).json()) == 0)

# ── BOOKKEEPING EXPORT ──────────────────────────────────────────────────
print("\n-- BOOKKEEPING EXPORT --")
r = requests.get(f"{BASE}/api/project/export/bookkeeping", headers=auth(token))
test("Bookkeeping export works", r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", ""))
r = requests.get(f"{BASE}/api/project/export/bookkeeping")
test("Bookkeeping requires auth", r.status_code == 401)

# ── RATE LIMITING (login) ───────────────────────────────────────────────
print("\n-- LOGIN RATE LIMITING --")
statuses = []
for _ in range(35):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": "brute", "password": "wrong"})
    statuses.append(r.status_code)
test("Login rate limiting active", 429 in statuses)

# ── CLEANUP ─────────────────────────────────────────────────────────────
requests.delete(f"{BASE}/api/project/draws/{draw_id}", headers=auth(token))

# ── SUMMARY ─────────────────────────────────────────────────────────────
print("\n" + "=" * 70)
passed = sum(1 for s, _, _ in RESULTS if s == "PASS")
failed = sum(1 for s, _, _ in RESULTS if s == "FAIL")
print(f"TOTAL: {passed} passed, {failed} failed out of {len(RESULTS)} tests")
if failed:
    print("\nFailed tests:")
    for s, name, detail in RESULTS:
        if s == "FAIL":
            print(f"  [X] {name}" + (f" -- {detail}" if detail else ""))
print("=" * 70)
