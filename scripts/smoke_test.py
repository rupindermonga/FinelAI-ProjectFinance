#!/usr/bin/env python3
"""
Pre-deploy smoke test for Finel AI Projects.

Runs in ~60 seconds. Tests the full live stack:
  1. Server is reachable
  2. Login works
  3. Health endpoint responds
  4. Upload is fast (< 5s) — no blocking Gemini calls
  5. Worker is alive (heartbeat < 90s old)
  6. Gemini keys available

Usage:
  python scripts/smoke_test.py                          # hits production
  python scripts/smoke_test.py --url http://localhost:8000  # hits local
  python scripts/smoke_test.py --url https://projects.finel.ai --user rupinder.monga@finel.ai --password <pw>
"""
import sys, time, argparse, textwrap
import urllib.request, urllib.error, json, io

# ── Config ────────────────────────────────────────────────────────────────────
BASE = "https://projects.finel.ai"
USER = "rupinder.monga@finel.ai"
PASS = ""  # set via --password or env SMOKE_PASSWORD

PASS_FAIL = {"PASS": "\033[32m✓ PASS\033[0m", "FAIL": "\033[31m✗ FAIL\033[0m", "WARN": "\033[33m⚠ WARN\033[0m"}

results = []


def check(name, passed, detail="", warn=False):
    status = "WARN" if warn and not passed else ("PASS" if passed else "FAIL")
    results.append((name, status, detail))
    symbol = PASS_FAIL[status]
    print(f"  {symbol}  {name}" + (f"  ({detail})" if detail else ""))
    return passed


def req(method, path, token=None, data=None, files=None, timeout=10):
    url = BASE + path
    headers = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    if data and not files:
        body = json.dumps(data).encode()
        headers["Content-Type"] = "application/json"
        r = urllib.request.Request(url, data=body, headers=headers, method=method)
    elif files:
        boundary = b"----FormBoundary7MA4YWxkTrZu0gW"
        body = b""
        for name, (fname, content, ctype) in files.items():
            body += b"--" + boundary + b"\r\n"
            body += f'Content-Disposition: form-data; name="{name}"; filename="{fname}"\r\n'.encode()
            body += f"Content-Type: {ctype}\r\n\r\n".encode()
            body += content + b"\r\n"
        body += b"--" + boundary + b"--\r\n"
        headers["Content-Type"] = "multipart/form-data; boundary=" + boundary.decode()
        r = urllib.request.Request(url, data=body, headers=headers, method=method)
    else:
        r = urllib.request.Request(url, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, {}
    except Exception as e:
        return 0, {"error": str(e)}


def main():
    global BASE, USER, PASS

    parser = argparse.ArgumentParser(description="Finel AI smoke test")
    parser.add_argument("--url", default=BASE)
    parser.add_argument("--user", default=USER)
    parser.add_argument("--password", default="")
    args = parser.parse_args()
    BASE = args.url.rstrip("/")
    USER = args.user
    PASS = args.password or input("Password: ")

    print(f"\n{'='*55}")
    print(f"  Finel AI Smoke Test  →  {BASE}")
    print(f"{'='*55}\n")

    # 1. Server reachable
    t0 = time.time()
    status, _ = req("GET", "/api/auth/me")
    elapsed = time.time() - t0
    check("Server reachable", status in (200, 401, 422), f"{elapsed*1000:.0f}ms")

    # 2. Login
    import urllib.parse
    url = BASE + "/api/auth/login"
    body = urllib.parse.urlencode({"username": USER, "password": PASS}).encode()
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        with urllib.request.urlopen(
            urllib.request.Request(url, data=body, headers=headers, method="POST"), timeout=10
        ) as resp:
            login_data = json.loads(resp.read())
            token = login_data.get("access_token")
            check("Login succeeds", bool(token), f"user={USER}")
    except Exception as e:
        check("Login succeeds", False, str(e))
        print("\n  Cannot continue without a valid token. Check credentials.\n")
        sys.exit(1)

    # 3. Health endpoint
    status, health = req("GET", "/api/admin/health", token=token)
    check("Health endpoint returns 200", status == 200)
    if status == 200:
        worker_alive = health.get("worker", {}).get("alive", False)
        secs_ago = health.get("worker", {}).get("last_heartbeat_secs_ago")
        check("Worker is alive", worker_alive,
              f"last heartbeat {secs_ago}s ago" if secs_ago else "no heartbeat yet",
              warn=True)

        keys_avail = health.get("gemini", {}).get("keys_available", 0)
        keys_total = health.get("gemini", {}).get("keys_total", 0)
        paid = health.get("gemini", {}).get("paid_key_configured", False)
        check("Gemini paid key configured", paid)
        check("At least 1 Gemini key available", keys_avail > 0,
              f"{keys_avail}/{keys_total} available", warn=True)

        err_rate = health.get("pipeline", {}).get("error_rate_pct_recent50", 0)
        check("Error rate < 20%", err_rate < 20, f"{err_rate}%", warn=True)

        stuck = health.get("pipeline", {}).get("stuck", 0)
        check("No permanently stuck invoices", stuck == 0, f"{stuck} stuck", warn=True)

    # 4. Upload is fast
    fake_pdf = b"%PDF-1.4 smoke test invoice"
    t_upload = time.time()
    status, upload_data = req("POST", "/api/upload", token=token,
                              files={"files": ("smoke_test.pdf", fake_pdf, "application/pdf")})
    upload_elapsed = time.time() - t_upload
    check("Upload returns quickly (< 5s)", upload_elapsed < 5.0, f"{upload_elapsed:.1f}s")
    check("Upload returns 200", status == 200)

    # Clean up test invoice
    if status == 200:
        results_list = upload_data.get("results", [])
        for r in results_list:
            if r.get("invoice_id"):
                req("DELETE", f"/api/invoices/{r['invoice_id']}", token=token)

    # 5. Stats endpoint
    status, stats = req("GET", "/api/invoices/stats", token=token)
    check("Stats endpoint returns 200", status == 200)

    # ── Summary ──────────────────────────────────────────────────────
    print(f"\n{'='*55}")
    fails   = sum(1 for _, s, _ in results if s == "FAIL")
    warns   = sum(1 for _, s, _ in results if s == "WARN")
    passes  = sum(1 for _, s, _ in results if s == "PASS")
    total   = len(results)
    print(f"  Results: {passes}/{total} passed, {warns} warnings, {fails} failures")
    if fails == 0:
        print("  \033[32m✓ SMOKE TEST PASSED — safe to deploy\033[0m")
    else:
        print("  \033[31m✗ SMOKE TEST FAILED — fix issues before deploying\033[0m")
    print(f"{'='*55}\n")
    sys.exit(0 if fails == 0 else 1)


if __name__ == "__main__":
    main()
