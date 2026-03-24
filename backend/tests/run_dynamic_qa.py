"""Deep dynamic security & QA audit — draws, claims, FX, project finance, auth, IDOR, validation."""
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
    import os
    if password is None:
        password = os.getenv("ADMIN_PASSWORD", "Admin@2026!")
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    return r.json().get("access_token") if r.status_code == 200 else None


def auth(token):
    return {"Authorization": f"Bearer {token}"}


print("=" * 70)
print("DEEP DYNAMIC SECURITY & QA AUDIT")
print("=" * 70)

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

r = requests.get(f"{BASE}/api/invoices", headers={"Authorization": "Bearer garbage.token.here"})
test("Garbage JWT = 401", r.status_code == 401)

ts = str(int(time.time()))
r = requests.post(f"{BASE}/api/auth/register", json={"username": f"qa_{ts}", "email": f"qa_{ts}@example.com", "password": "StrongP@ss1"})
test("Register valid user", r.status_code == 200)
user2_token = login(f"qa_{ts}", "StrongP@ss1")
test("User2 login", user2_token is not None)

r = requests.post(f"{BASE}/api/auth/register", json={"username": "ab", "email": f"short_{ts}@example.com", "password": "StrongP@ss1"})
test("Short username rejected", r.status_code == 422)

r = requests.post(f"{BASE}/api/auth/register", json={"username": f"bad_{ts}", "email": f"bad_{ts}@qa.local", "password": "StrongP@ss1"})
test("Invalid .local email rejected", r.status_code == 422)

r = requests.post(f"{BASE}/api/auth/register", json={"username": f"short_{ts}", "email": f"sp_{ts}@example.com", "password": "abc"})
test("Short password rejected", r.status_code == 422)

# ── RATE LIMITING ────────────────────────────────────────────────────────
print("\n-- RATE LIMITING --")
statuses = []
for i in range(12):
    r = requests.post(f"{BASE}/api/auth/login", json={"username": "brute", "password": "wrong"})
    statuses.append(r.status_code)
test("Login rate limiting (429 appears)", 429 in statuses, f"last 3: {statuses[-3:]}")

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
test("Export ?token= rejected (header only)", r.status_code == 401)
r = requests.get(f"{BASE}/api/export/excel", headers=auth(token))
test("Export with Bearer works", r.status_code == 200)

# ── UPLOAD VALIDATION ───────────────────────────────────────────────────
print("\n-- UPLOAD VALIDATION --")
r = requests.post(f"{BASE}/api/upload", headers=auth(token), files={"files": ("fake.pdf", b"this is not a pdf", "application/pdf")})
test("Fake PDF rejected", r.status_code == 200 and any(item.get("status") == "rejected" for item in r.json().get("results", [])))
r = requests.post(f"{BASE}/api/upload", headers=auth(token), files={"files": ("test.exe", b"MZ\x90\x00", "application/octet-stream")})
test("EXE extension rejected", r.status_code == 200 and any(item.get("status") == "rejected" for item in r.json().get("results", [])))

# ── IDOR / CROSS-USER ISOLATION ─────────────────────────────────────────
print("\n-- IDOR / CROSS-USER ISOLATION --")
admin_invs = requests.get(f"{BASE}/api/invoices", headers=auth(token)).json().get("items", [])
user2_invs = requests.get(f"{BASE}/api/invoices", headers=auth(user2_token)).json().get("items", [])
test("User2 sees 0 invoices (admin has some)", len(user2_invs) == 0)

admin_cols = requests.get(f"{BASE}/api/columns", headers=auth(token)).json()
user2_cols = requests.get(f"{BASE}/api/columns", headers=auth(user2_token)).json()
admin_col_ids = {c["id"] for c in admin_cols}
user2_col_ids = {c["id"] for c in user2_cols}
test("Column IDs are user-scoped", admin_col_ids.isdisjoint(user2_col_ids))

if admin_cols:
    r = requests.put(f"{BASE}/api/columns/{admin_cols[0]['id']}", headers=auth(user2_token), json={"field_label": "HACKED"})
    test("User2 cant modify admin column", r.status_code in (403, 404))

r = requests.get(f"{BASE}/api/admin/api-keys", headers=auth(user2_token))
test("Non-admin blocked from admin API keys", r.status_code == 403)

# ── PROJECT FINANCE ─────────────────────────────────────────────────────
print("\n-- PROJECT FINANCE --")
r = requests.get(f"{BASE}/api/project/dashboard", headers=auth(token))
test("Dashboard loads", r.status_code == 200 and r.json().get("project") is not None)
dash = r.json()

test("5 cost categories", len(dash.get("categories", [])) == 5)
fb = next((c for c in dash.get("categories", []) if c["name"] == "Fiber Build"), None)
test("Fiber Build is per-subdivision", fb is not None and fb.get("is_per_subdivision"))

r = requests.get(f"{BASE}/api/project/subdivisions", headers=auth(token))
test("5 subdivisions", r.status_code == 200 and len(r.json()) == 5)

cats = requests.get(f"{BASE}/api/project/categories", headers=auth(token)).json()
test("Categories API works", len(cats) == 5)

# Budget validation
if cats:
    r = requests.put(f"{BASE}/api/project/categories/{cats[0]['id']}", headers=auth(token), json={"budget": -100})
    test("Negative budget rejected on update", r.status_code == 400)
    r = requests.post(f"{BASE}/api/project/categories", headers=auth(token), json={"name": "Test", "budget": -50})
    test("Negative budget rejected on create", r.status_code == 400)
    r = requests.post(f"{BASE}/api/project/categories", headers=auth(token), json={"name": cats[0]["name"], "budget": 0})
    test("Duplicate category rejected", r.status_code == 400)

# ── DRAWS ────────────────────────────────────────────────────────────────
print("\n-- DRAWS --")
r = requests.get(f"{BASE}/api/project/draws", headers=auth(token))
existing_draws = r.json()
test("List draws", r.status_code == 200)

# Clean up test draws from earlier
for d in existing_draws:
    requests.delete(f"{BASE}/api/project/draws/{d['id']}", headers=auth(token))

# Create draw
r = requests.post(f"{BASE}/api/project/draws", headers=auth(token), json={"draw_number": 1, "fx_rate": 1.3847, "status": "draft"})
test("Create Draw 1", r.status_code == 200)
draw1 = r.json()
draw1_id = draw1["id"]

# Duplicate draw number
r = requests.post(f"{BASE}/api/project/draws", headers=auth(token), json={"draw_number": 1, "fx_rate": 1.40})
test("Duplicate draw number rejected", r.status_code == 400)

# Update draw
r = requests.put(f"{BASE}/api/project/draws/{draw1_id}", headers=auth(token), json={"fx_rate": 1.3900, "status": "submitted", "submission_date": "2026-03-20"})
test("Update draw", r.status_code == 200 and r.json()["fx_rate"] == 1.39)

# Assign invoices to draw
processed = [i for i in admin_invs if i["status"] == "processed"]
if processed:
    inv_ids = [i["id"] for i in processed[:2]]
    r = requests.put(f"{BASE}/api/project/draws/{draw1_id}/invoices", headers=auth(token), json=inv_ids)
    test("Assign invoices to draw", r.status_code == 200 and r.json()["invoice_count"] == len(inv_ids))

    r = requests.get(f"{BASE}/api/project/draws/{draw1_id}/invoices", headers=auth(token))
    test("Get draw invoices", r.status_code == 200 and len(r.json()) == len(inv_ids))

# User2 cant access admin draws
r = requests.get(f"{BASE}/api/project/draws", headers=auth(user2_token))
test("User2 sees own draws (empty)", r.status_code == 200 and len(r.json()) == 0)

r = requests.put(f"{BASE}/api/project/draws/{draw1_id}", headers=auth(user2_token), json={"fx_rate": 999})
test("User2 cant update admin draw", r.status_code == 404)

if processed:
    r = requests.put(f"{BASE}/api/project/draws/{draw1_id}/invoices", headers=auth(user2_token), json=[processed[0]["id"]])
    test("User2 cant assign to admin draw", r.status_code == 404)

# ── CLAIMS ───────────────────────────────────────────────────────────────
print("\n-- CLAIMS --")
old_claims = requests.get(f"{BASE}/api/project/claims", headers=auth(token)).json()
for c in old_claims:
    requests.delete(f"{BASE}/api/project/claims/{c['id']}", headers=auth(token))

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 1, "claim_type": "provincial", "fx_rate": 1.35})
test("Create provincial claim", r.status_code == 200)
prov1_id = r.json()["id"]

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 1, "claim_type": "federal", "fx_rate": 1.36})
test("Create federal claim", r.status_code == 200)
fed1_id = r.json()["id"]

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 2, "claim_type": "municipal", "fx_rate": 1.0})
test("Invalid claim_type rejected", r.status_code == 400)

r = requests.post(f"{BASE}/api/project/claims", headers=auth(token), json={"claim_number": 1, "claim_type": "provincial", "fx_rate": 1.0})
test("Duplicate provincial claim 1 rejected", r.status_code == 400)

test("Fed claim 1 created (same # as prov)", fed1_id is not None)

r = requests.put(f"{BASE}/api/project/claims/{prov1_id}", headers=auth(token), json={"fx_rate": 1.3600, "status": "submitted"})
test("Update claim", r.status_code == 200)

if processed:
    r = requests.put(f"{BASE}/api/project/claims/{prov1_id}/invoices", headers=auth(token), json=[i["id"] for i in processed[:2]])
    test("Assign invoices to prov claim", r.status_code == 200)

r = requests.put(f"{BASE}/api/project/claims/{fed1_id}/copy-from-draw/{draw1_id}", headers=auth(token), json={})
test("Copy draw invoices to federal claim", r.status_code == 200)
if processed:
    test("Federal claim has draw invoices", r.json()["invoice_count"] >= 1)

r = requests.get(f"{BASE}/api/project/claims/{fed1_id}/invoices", headers=auth(token))
test("Get claim invoices", r.status_code == 200)

# User2 IDOR on claims
r = requests.put(f"{BASE}/api/project/claims/{prov1_id}", headers=auth(user2_token), json={"fx_rate": 999})
test("User2 cant update admin claim", r.status_code == 404)
r = requests.delete(f"{BASE}/api/project/claims/{prov1_id}", headers=auth(user2_token))
test("User2 cant delete admin claim", r.status_code == 404)
r = requests.put(f"{BASE}/api/project/claims/{prov1_id}/invoices", headers=auth(user2_token), json=[])
test("User2 cant assign to admin claim", r.status_code == 404)

# ── FX RATE ──────────────────────────────────────────────────────────────
print("\n-- FX RATE (Bank of Canada) --")
r = requests.get(f"{BASE}/api/project/fx-rate")
test("FX rate endpoint works", r.status_code == 200)
fx = r.json()
test("Rate > 1.0 (USD stronger than CAD)", fx.get("rate", 0) > 1.0)
test("Source is bank_of_canada", fx.get("source") == "bank_of_canada")

r = requests.get(f"{BASE}/api/project/fx-rate?date=2025-10-21")
test("FX rate for specific date", r.status_code == 200 and r.json().get("rate", 0) > 1.0)

r = requests.get(f"{BASE}/api/project/fx-rate?date=2025-12-25")
test("FX rate for holiday (fallback to nearby)", r.status_code == 200)

# ── PAYMENT VALIDATION ──────────────────────────────────────────────────
print("\n-- PAYMENT VALIDATION --")
if processed:
    inv = processed[0]
    r = requests.post(f"{BASE}/api/project/payments", headers=auth(token), json={"invoice_id": inv["id"], "amount": -50, "payment_date": "2026-03-24"})
    test("Negative payment rejected", r.status_code == 400)

    if inv.get("total_due"):
        r = requests.post(f"{BASE}/api/project/payments", headers=auth(token), json={"invoice_id": inv["id"], "amount": inv["total_due"] * 10, "payment_date": "2026-03-24"})
        test("Overpayment rejected", r.status_code == 400, f"status={r.status_code}")

    r = requests.post(f"{BASE}/api/project/payments", headers=auth(user2_token), json={"invoice_id": inv["id"], "amount": 1, "payment_date": "2026-03-24"})
    test("User2 cant pay admin invoice", r.status_code == 404)

# ── ALLOCATION VALIDATION ───────────────────────────────────────────────
print("\n-- ALLOCATION VALIDATION --")
if processed and cats:
    inv = processed[0]
    r = requests.put(f"{BASE}/api/project/allocations/{inv['id']}", headers=auth(token), json=[{"invoice_id": inv["id"], "category_id": cats[0]["id"], "percentage": -10}])
    test("Negative allocation % rejected", r.status_code == 400)

    r = requests.put(f"{BASE}/api/project/allocations/{inv['id']}", headers=auth(token), json=[
        {"invoice_id": inv["id"], "category_id": cats[0]["id"], "percentage": 60},
        {"invoice_id": inv["id"], "category_id": cats[1]["id"], "percentage": 60},
    ])
    test("Allocation >100% rejected", r.status_code == 400)

    r = requests.put(f"{BASE}/api/project/allocations/{inv['id']}", headers=auth(token), json=[{"invoice_id": inv["id"], "category_id": 99999, "percentage": 100}])
    test("Non-existent category rejected", r.status_code == 404)

    r = requests.put(f"{BASE}/api/project/allocations/{inv['id']}", headers=auth(user2_token), json=[])
    test("User2 cant allocate admin invoice", r.status_code == 404)

    r = requests.put(f"{BASE}/api/project/allocations/{inv['id']}", headers=auth(token), json=[{"invoice_id": inv["id"], "category_id": cats[0]["id"], "percentage": 100}])
    test("Valid 100% allocation", r.status_code == 200)

# ── CROSS-USER SUBDIVISION BUDGET ───────────────────────────────────────
print("\n-- CROSS-USER SUBDIVISION BUDGET --")
u2_dash = requests.get(f"{BASE}/api/project/dashboard", headers=auth(user2_token)).json()
if u2_dash.get("project"):
    u2_cats = requests.get(f"{BASE}/api/project/categories", headers=auth(user2_token)).json()
    admin_sds = requests.get(f"{BASE}/api/project/subdivisions", headers=auth(token)).json()
    if u2_cats and admin_sds:
        fb_cat = next((c for c in u2_cats if c.get("is_per_subdivision")), None)
        if fb_cat:
            r = requests.put(f"{BASE}/api/project/categories/{fb_cat['id']}/subdivision-budgets", headers=auth(user2_token),
                             json=[{"subdivision_id": admin_sds[0]["id"], "budget": 99999}])
            test("Cross-user subdivision budget rejected", r.status_code in (404, 400), f"status={r.status_code}")

# ── DASHBOARD INTEGRITY ─────────────────────────────────────────────────
print("\n-- DASHBOARD INTEGRITY --")
r = requests.get(f"{BASE}/api/project/dashboard", headers=auth(token))
d = r.json()
test("Dashboard has draws array", "draws" in d)
test("Dashboard has provincial_claims", "provincial_claims" in d)
test("Dashboard has federal_claims", "federal_claims" in d)
test("Dashboard has invoices_without_draw", "invoices_without_draw" in d)
test("Dashboard has invoices_without_claim", "invoices_without_claim" in d)
test("Draws count >= 1", len(d.get("draws", [])) >= 1)
test("Provincial claims >= 1", len(d.get("provincial_claims", [])) >= 1)
test("Federal claims >= 1", len(d.get("federal_claims", [])) >= 1)

# ── BOOKKEEPING EXPORT ──────────────────────────────────────────────────
print("\n-- BOOKKEEPING EXPORT --")
r = requests.get(f"{BASE}/api/project/export/bookkeeping", headers=auth(token))
test("Bookkeeping export works", r.status_code == 200 and "spreadsheetml" in r.headers.get("content-type", ""))
r = requests.get(f"{BASE}/api/project/export/bookkeeping")
test("Bookkeeping export requires auth", r.status_code == 401)

# ── SSE ─────────────────────────────────────────────────────────────────
print("\n-- SSE --")
r = requests.get(f"{BASE}/api/invoices/stream", stream=True, timeout=3)
test("SSE without token = 401", r.status_code == 401)
r = requests.get(f"{BASE}/api/invoices/stream?token={token}", stream=True, timeout=3)
test("SSE with token works", r.status_code == 200 and "text/event-stream" in r.headers.get("content-type", ""))
r.close()

# ── DELETE CLEANUP ──────────────────────────────────────────────────────
print("\n-- DRAW/CLAIM DELETE --")
r = requests.delete(f"{BASE}/api/project/draws/{draw1_id}", headers=auth(token))
test("Delete draw", r.status_code == 200)

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
