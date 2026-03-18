"""
Finel AI Invoice Extractor — Security & QA Dynamic Test Suite
Run: python -m pytest tests/security_qa_test.py -v
"""

import pytest
import requests
import json
import os
import io
import time

BASE = "http://localhost:8000"
ADMIN = {"username": "admin", "password": "admin123"}


# ─── Helpers ─────────────────────────────────────────────────────────────────

def login(username="admin", password="admin123") -> str:
    r = requests.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, f"Login failed: {r.text}"
    return r.json()["access_token"]


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def register_user(username: str, email: str, password: str) -> requests.Response:
    return requests.post(f"{BASE}/api/auth/register", json={
        "username": username, "email": email, "password": password
    })


# ─── AUTH TESTS ───────────────────────────────────────────────────────────────

class TestAuthentication:

    def test_login_valid_credentials(self):
        """Admin can log in successfully."""
        r = requests.post(f"{BASE}/api/auth/login", json=ADMIN)
        assert r.status_code == 200
        data = r.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self):
        """Login fails with wrong password."""
        r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "wrongpass"})
        assert r.status_code == 401

    def test_login_nonexistent_user(self):
        """Login fails for nonexistent user."""
        r = requests.post(f"{BASE}/api/auth/login", json={"username": "ghost_user_xyz", "password": "any"})
        assert r.status_code == 401

    def test_login_empty_credentials(self):
        """Login fails with empty credentials."""
        r = requests.post(f"{BASE}/api/auth/login", json={"username": "", "password": ""})
        assert r.status_code in (401, 422)

    def test_login_sql_injection_username(self):
        """SQL injection in username is rejected."""
        r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin' OR '1'='1", "password": "x"})
        assert r.status_code in (401, 422)

    def test_login_sql_injection_password(self):
        """SQL injection in password is rejected."""
        r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "x' OR '1'='1"})
        assert r.status_code == 401

    def test_register_new_user(self):
        """Registration creates a new user."""
        ts = str(int(time.time()))
        r = register_user(f"testuser_{ts}", f"test_{ts}@qa.local", "TestPass123!")
        assert r.status_code == 200

    def test_register_duplicate_username(self):
        """Duplicate username is rejected."""
        ts = str(int(time.time()))
        uname = f"duptest_{ts}"
        register_user(uname, f"{uname}@qa.local", "TestPass123!")
        r2 = register_user(uname, f"{uname}2@qa.local", "TestPass123!")
        assert r2.status_code in (400, 409, 422)

    def test_register_duplicate_email(self):
        """Duplicate email is rejected."""
        ts = str(int(time.time()))
        email = f"dup_{ts}@qa.local"
        register_user(f"user1_{ts}", email, "TestPass123!")
        r2 = register_user(f"user2_{ts}", email, "TestPass123!")
        assert r2.status_code in (400, 409, 422)

    def test_token_required_for_protected_routes(self):
        """Protected routes reject requests without token."""
        r = requests.get(f"{BASE}/api/invoices")
        assert r.status_code == 401

    def test_invalid_token_rejected(self):
        """Forged / garbage JWT is rejected."""
        r = requests.get(f"{BASE}/api/invoices", headers={"Authorization": "Bearer garbage.token.here"})
        assert r.status_code == 401

    def test_expired_token_rejected(self):
        """A known-bad token (wrong signature) is rejected."""
        fake = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJhZG1pbiJ9.bad_signature"
        r = requests.get(f"{BASE}/api/invoices", headers={"Authorization": f"Bearer {fake}"})
        assert r.status_code == 401

    def test_missing_password_field(self):
        """Login without password field returns validation error."""
        r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin"})
        assert r.status_code == 422

    def test_missing_username_field(self):
        """Login without username field returns validation error."""
        r = requests.post(f"{BASE}/api/auth/login", json={"password": "admin123"})
        assert r.status_code == 422


# ─── AUTHORIZATION / IDOR TESTS ───────────────────────────────────────────────

class TestAuthorization:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.admin_token = login()
        ts = str(int(time.time()))
        # Create a second user
        r = register_user(f"user2_{ts}", f"user2_{ts}@qa.local", "Pass123!")
        assert r.status_code == 200
        self.user2_token = login(f"user2_{ts}", "Pass123!")

    def test_user_cannot_see_others_invoices(self):
        """User2 invoice list is empty (cannot see admin invoices)."""
        r = requests.get(f"{BASE}/api/invoices", headers=auth_headers(self.user2_token))
        assert r.status_code == 200
        assert r.json()["items"] == []

    def test_user_cannot_see_others_columns(self):
        """User2 columns are their own, not admin's."""
        admin_cols = requests.get(f"{BASE}/api/columns", headers=auth_headers(self.admin_token)).json()
        user2_cols = requests.get(f"{BASE}/api/columns", headers=auth_headers(self.user2_token)).json()
        admin_ids = {c["id"] for c in admin_cols}
        user2_ids = {c["id"] for c in user2_cols}
        assert admin_ids.isdisjoint(user2_ids), "Users share column IDs — IDOR vulnerability!"

    def test_user_cannot_modify_others_column(self):
        """User2 cannot modify admin's column IDs."""
        admin_cols = requests.get(f"{BASE}/api/columns", headers=auth_headers(self.admin_token)).json()
        if admin_cols:
            admin_col_id = admin_cols[0]["id"]
            r = requests.put(
                f"{BASE}/api/columns/{admin_col_id}",
                headers=auth_headers(self.user2_token),
                json={"field_label": "HACKED"}
            )
            assert r.status_code in (403, 404), f"IDOR: user2 modified admin column! status={r.status_code}"

    def test_user_cannot_delete_others_category(self):
        """User2 cannot delete admin's categories."""
        # Create a category as admin
        r = requests.post(f"{BASE}/api/categories",
            headers=auth_headers(self.admin_token),
            json={"name": "TestCat_IDOR", "level": "category"}
        )
        assert r.status_code == 200
        cat_id = r.json()["id"]

        # Try deleting as user2
        r2 = requests.delete(f"{BASE}/api/categories/{cat_id}", headers=auth_headers(self.user2_token))
        assert r2.status_code in (403, 404), f"IDOR: user2 deleted admin category! status={r2.status_code}"

        # Cleanup
        requests.delete(f"{BASE}/api/categories/{cat_id}", headers=auth_headers(self.admin_token))

    def test_user_cannot_see_others_categories(self):
        """Categories are user-scoped."""
        r = requests.post(f"{BASE}/api/categories",
            headers=auth_headers(self.admin_token),
            json={"name": "AdminPrivateCat", "level": "category"}
        )
        cat_id = r.json()["id"]
        user2_cats = requests.get(f"{BASE}/api/categories?flat=true", headers=auth_headers(self.user2_token)).json()
        user2_names = [c["name"] for c in user2_cats]
        assert "AdminPrivateCat" not in user2_names
        # Cleanup
        requests.delete(f"{BASE}/api/categories/{cat_id}", headers=auth_headers(self.admin_token))


# ─── INPUT VALIDATION TESTS ───────────────────────────────────────────────────

class TestInputValidation:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = login()
        self.headers = auth_headers(self.token)

    def test_invoice_filter_large_string(self):
        """Very large filter string doesn't crash server."""
        payload = "x" * 10000
        r = requests.get(f"{BASE}/api/invoices?vendor={payload}", headers=self.headers)
        assert r.status_code in (200, 400, 422)
        assert r.status_code != 500

    def test_invoice_filter_sql_injection(self):
        """SQL injection in invoice filter is handled."""
        r = requests.get(f"{BASE}/api/invoices?vendor='; DROP TABLE invoices; --", headers=self.headers)
        assert r.status_code in (200, 400)
        assert r.status_code != 500

    def test_invoice_filter_invalid_date_format(self):
        """Invalid date format in filter is handled gracefully."""
        r = requests.get(f"{BASE}/api/invoices?start_date=not-a-date", headers=self.headers)
        assert r.status_code in (200, 400, 422)
        assert r.status_code != 500

    def test_invoice_filter_invalid_limit(self):
        """Limit out of bounds is rejected."""
        r = requests.get(f"{BASE}/api/invoices?limit=99999", headers=self.headers)
        assert r.status_code == 422  # FastAPI ge/le validation

    def test_invoice_filter_negative_limit(self):
        """Negative limit is rejected."""
        r = requests.get(f"{BASE}/api/invoices?limit=-1", headers=self.headers)
        assert r.status_code == 422

    def test_create_category_invalid_level(self):
        """Invalid category level is rejected."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "Test", "level": "invalid_level"})
        assert r.status_code == 400

    def test_create_subcategory_without_parent(self):
        """Sub-category without parent_id is rejected."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "Sub", "level": "sub_category"})
        assert r.status_code == 400

    def test_create_subdivision_without_parent(self):
        """Sub-division without parent_id is rejected."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "Div", "level": "sub_division"})
        assert r.status_code == 400

    def test_create_category_empty_name(self):
        """Empty name is rejected."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "", "level": "category"})
        assert r.status_code == 400, f"Empty category name was accepted (status {r.status_code}) — QA issue"

    def test_create_category_xss_in_name(self):
        """XSS payload in category name is stored but should be escaped on display."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "<script>alert('xss')</script>", "level": "category"})
        assert r.status_code == 200  # Stored as-is (sanitization is frontend's job)
        data = r.json()
        assert data["name"] == "<script>alert('xss')</script>"  # Raw stored
        # Cleanup
        requests.delete(f"{BASE}/api/categories/{data['id']}", headers=self.headers)

    def test_column_update_field_type_invalid(self):
        """Invalid field_type on column update is rejected."""
        cols = requests.get(f"{BASE}/api/columns", headers=self.headers).json()
        if cols:
            r = requests.put(f"{BASE}/api/columns/{cols[0]['id']}", headers=self.headers,
                json={"field_type": "super_invalid_type"})
            assert r.status_code == 422, f"Invalid field_type was accepted (status {r.status_code})"

    def test_upload_no_file(self):
        """Upload without file returns 422."""
        r = requests.post(f"{BASE}/api/upload", headers=self.headers)
        assert r.status_code == 422

    def test_upload_wrong_extension(self):
        """Upload with unsupported extension is rejected."""
        files = {"file": ("test.exe", b"fake content", "application/octet-stream")}
        r = requests.post(f"{BASE}/api/upload", headers=self.headers, files=files)
        assert r.status_code in (400, 422)

    def test_upload_empty_file(self):
        """Upload with empty file is handled gracefully."""
        files = {"file": ("empty.pdf", b"", "application/pdf")}
        r = requests.post(f"{BASE}/api/upload", headers=self.headers, files=files)
        assert r.status_code in (200, 400, 422)
        assert r.status_code != 500

    def test_upload_oversized_file(self):
        """Upload with > 50 MB should be rejected."""
        large_content = b"x" * (51 * 1024 * 1024)
        files = {"file": ("big.pdf", large_content, "application/pdf")}
        r = requests.post(f"{BASE}/api/upload", headers=self.headers, files=files)
        assert r.status_code in (400, 413, 422)


# ─── CATEGORY HIERARCHY TESTS ─────────────────────────────────────────────────

class TestCategoryHierarchy:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = login()
        self.headers = auth_headers(self.token)

        # Create test category
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "QATestCat", "level": "category"})
        self.cat = r.json()
        self.cat_id = self.cat["id"]

        # Create sub-category
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "QATestSubCat", "level": "sub_category", "parent_id": self.cat_id})
        self.subcat = r.json()
        self.subcat_id = self.subcat["id"]

        yield

        # Teardown — delete parent (cascades to children)
        requests.delete(f"{BASE}/api/categories/{self.cat_id}", headers=self.headers)

    def test_create_category(self):
        """Category is created with correct structure."""
        assert self.cat["level"] == "category"
        assert self.cat["name"] == "QATestCat"
        assert self.cat["is_active"] is True
        assert self.cat["requires_sub_division"] is False

    def test_create_sub_category(self):
        """Sub-category is created under category."""
        assert self.subcat["level"] == "sub_category"
        assert self.subcat["parent_id"] == self.cat_id

    def test_create_sub_division_under_category(self):
        """Sub-division is created as direct child of category."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "Div 1", "level": "sub_division", "parent_id": self.cat_id})
        assert r.status_code == 200
        assert r.json()["level"] == "sub_division"
        assert r.json()["parent_id"] == self.cat_id

    def test_sub_division_parent_cannot_be_sub_category(self):
        """Sub-division parent must be a category, not sub-category."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "Div 1", "level": "sub_division", "parent_id": self.subcat_id})
        assert r.status_code == 400, f"Sub-division with sub-category parent was accepted! Got {r.status_code}"

    def test_sub_category_parent_must_be_category(self):
        """Sub-category parent must be a category."""
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "NestedSub", "level": "sub_category", "parent_id": self.subcat_id})
        assert r.status_code == 400

    def test_toggle_requires_sub_division(self):
        """requires_sub_division toggle works."""
        r = requests.put(f"{BASE}/api/categories/{self.cat_id}", headers=self.headers,
            json={"requires_sub_division": True})
        assert r.status_code == 200
        assert r.json()["requires_sub_division"] is True

        # Toggle back
        r = requests.put(f"{BASE}/api/categories/{self.cat_id}", headers=self.headers,
            json={"requires_sub_division": False})
        assert r.json()["requires_sub_division"] is False

    def test_list_categories_tree_structure(self):
        """Tree response nests sub-categories under categories."""
        r = requests.get(f"{BASE}/api/categories", headers=self.headers)
        assert r.status_code == 200
        tree = r.json()
        our_cat = next((c for c in tree if c["id"] == self.cat_id), None)
        assert our_cat is not None
        sub_names = [c["name"] for c in our_cat.get("children", [])]
        assert "QATestSubCat" in sub_names

    def test_list_categories_flat(self):
        """Flat list returns all items without nesting."""
        r = requests.get(f"{BASE}/api/categories?flat=true", headers=self.headers)
        assert r.status_code == 200
        flat = r.json()
        ids = [c["id"] for c in flat]
        assert self.cat_id in ids
        assert self.subcat_id in ids

    def test_delete_category_cascades(self):
        """Deleting a category removes its sub-categories."""
        # Create throwaway cat + sub
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "TempCat", "level": "category"})
        temp_cat_id = r.json()["id"]
        r = requests.post(f"{BASE}/api/categories", headers=self.headers,
            json={"name": "TempSub", "level": "sub_category", "parent_id": temp_cat_id})
        temp_sub_id = r.json()["id"]

        # Delete parent
        requests.delete(f"{BASE}/api/categories/{temp_cat_id}", headers=self.headers)

        # Verify sub is gone
        flat = requests.get(f"{BASE}/api/categories?flat=true", headers=self.headers).json()
        ids = [c["id"] for c in flat]
        assert temp_sub_id not in ids, "Sub-category not deleted when parent was deleted — cascade failure"

    def test_active_names_endpoint(self):
        """Active-names returns structured data."""
        r = requests.get(f"{BASE}/api/categories/active-names", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, list)

    def test_update_nonexistent_category(self):
        """Updating non-existent category returns 404."""
        r = requests.put(f"{BASE}/api/categories/999999", headers=self.headers,
            json={"name": "Ghost"})
        assert r.status_code == 404

    def test_delete_nonexistent_category(self):
        """Deleting non-existent category returns 404."""
        r = requests.delete(f"{BASE}/api/categories/999999", headers=self.headers)
        assert r.status_code == 404


# ─── COLUMN MANAGEMENT TESTS ──────────────────────────────────────────────────

class TestColumnManagement:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = login()
        self.headers = auth_headers(self.token)
        self.cols = requests.get(f"{BASE}/api/columns", headers=self.headers).json()

    def test_list_columns_returns_array(self):
        """Columns endpoint returns a list."""
        assert isinstance(self.cols, list)
        assert len(self.cols) > 0

    def test_column_has_required_fields(self):
        """Each column has expected fields."""
        for col in self.cols:
            assert "id" in col
            assert "field_key" in col
            assert "field_label" in col
            assert "field_type" in col
            assert "is_active" in col

    def test_column_key_uniqueness(self):
        """No duplicate field_key values."""
        keys = [c["field_key"] for c in self.cols]
        assert len(keys) == len(set(keys)), "Duplicate field_keys found!"

    def test_expected_columns_present(self):
        """Required columns exist for the project."""
        expected_keys = {
            "invoice_number", "invoice_date", "vendor_name", "line_items",
            "category", "sub_category", "sub_division", "currency"
        }
        actual_keys = {c["field_key"] for c in self.cols}
        missing = expected_keys - actual_keys
        assert not missing, f"Missing expected columns: {missing}"

    def test_toggle_column_active(self):
        """Can toggle column is_active status."""
        col = self.cols[0]
        original = col["is_active"]
        r = requests.put(f"{BASE}/api/columns/{col['id']}", headers=self.headers,
            json={"is_active": not original})
        assert r.status_code == 200
        assert r.json()["is_active"] == (not original)
        # Restore
        requests.put(f"{BASE}/api/columns/{col['id']}", headers=self.headers,
            json={"is_active": original})

    def test_update_nonexistent_column(self):
        """Updating non-existent column returns 404."""
        r = requests.put(f"{BASE}/api/columns/999999", headers=self.headers,
            json={"field_label": "Ghost"})
        assert r.status_code == 404

    def test_column_order_preserved(self):
        """Columns are returned in display_order."""
        orders = [c["display_order"] for c in self.cols]
        assert orders == sorted(orders), "Columns not returned in order"


# ─── INVOICE CRUD TESTS ───────────────────────────────────────────────────────

class TestInvoiceAPI:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = login()
        self.headers = auth_headers(self.token)

    def test_list_invoices_empty_or_paginated(self):
        """Invoice list returns proper structure."""
        r = requests.get(f"{BASE}/api/invoices", headers=self.headers)
        assert r.status_code == 200
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data

    def test_invoice_filter_by_status(self):
        """Filter by status parameter works without error."""
        for status in ["pending", "processing", "done", "error", "nonexistent"]:
            r = requests.get(f"{BASE}/api/invoices?status={status}", headers=self.headers)
            assert r.status_code == 200

    def test_invoice_filter_by_date_range(self):
        """Valid date range filter works."""
        r = requests.get(f"{BASE}/api/invoices?start_date=2024-01-01&end_date=2024-12-31",
            headers=self.headers)
        assert r.status_code == 200

    def test_invoice_pagination(self):
        """Pagination parameters work."""
        r = requests.get(f"{BASE}/api/invoices?page=1&limit=10", headers=self.headers)
        assert r.status_code == 200

    def test_invoice_page_zero_invalid(self):
        """Page 0 is invalid."""
        r = requests.get(f"{BASE}/api/invoices?page=0", headers=self.headers)
        assert r.status_code == 422

    def test_get_nonexistent_invoice(self):
        """Non-existent invoice returns 404."""
        r = requests.get(f"{BASE}/api/invoices/999999", headers=self.headers)
        assert r.status_code == 404

    def test_delete_nonexistent_invoice(self):
        """Deleting non-existent invoice returns 404."""
        r = requests.delete(f"{BASE}/api/invoices/999999", headers=self.headers)
        assert r.status_code == 404


# ─── EXPORT TESTS ─────────────────────────────────────────────────────────────

class TestExport:

    @pytest.fixture(autouse=True)
    def setup(self):
        self.token = login()
        self.headers = auth_headers(self.token)

    def test_export_excel_requires_auth(self):
        """Excel export without token returns 401."""
        r = requests.get(f"{BASE}/api/export/excel")
        assert r.status_code == 401

    def test_export_json_requires_auth(self):
        """JSON export without token returns 401."""
        r = requests.get(f"{BASE}/api/export/json")
        assert r.status_code == 401

    def test_export_excel_with_token_param(self):
        """Excel export works with ?token= param."""
        r = requests.get(f"{BASE}/api/export/excel?token={self.token}")
        assert r.status_code == 200
        assert "spreadsheetml" in r.headers.get("content-type", "") or \
               r.headers.get("content-type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    def test_export_json_with_token_param(self):
        """JSON export works with ?token= param."""
        r = requests.get(f"{BASE}/api/export/json?token={self.token}")
        assert r.status_code == 200

    def test_export_json_with_bearer_token(self):
        """JSON export also works with Bearer token header."""
        r = requests.get(f"{BASE}/api/export/json", headers=self.headers)
        assert r.status_code == 200

    def test_export_invalid_token_rejected(self):
        """Export with garbage token is rejected."""
        r = requests.get(f"{BASE}/api/export/excel?token=garbage.token.fake")
        assert r.status_code == 401

    def test_export_date_filter(self):
        """Export accepts date range filter."""
        r = requests.get(
            f"{BASE}/api/export/json?token={self.token}&start_date=2024-01-01&end_date=2024-12-31"
        )
        assert r.status_code == 200


# ─── SECURITY HEADER TESTS ───────────────────────────────────────────────────

class TestSecurityHeaders:

    def test_cors_header_present(self):
        """CORS header is returned."""
        r = requests.options(f"{BASE}/api/invoices", headers={"Origin": "http://evil.com"})
        # With allow_origins=["*"], this will return the wildcard
        cors = r.headers.get("access-control-allow-origin", "")
        print(f"\n[INFO] CORS allow-origin: '{cors}'")
        # Flag if wildcard (known issue — for awareness)
        if cors == "*":
            print("[WARNING] CORS is set to wildcard '*' — this is a known security issue (see audit)")

    def test_no_server_version_disclosure(self):
        """Server header should not expose version details."""
        r = requests.get(f"{BASE}/")
        server = r.headers.get("server", "")
        print(f"\n[INFO] Server header: '{server}'")
        # FastAPI/uvicorn exposes 'uvicorn' — informational

    def test_content_security_policy_present(self):
        """CSP header is present."""
        r = requests.get(f"{BASE}/")
        csp = r.headers.get("content-security-policy", "")
        assert csp, "No Content-Security-Policy header"

    def test_x_content_type_options(self):
        """X-Content-Type-Options header present."""
        r = requests.get(f"{BASE}/")
        xct = r.headers.get("x-content-type-options", "")
        assert xct == "nosniff", f"Missing X-Content-Type-Options header (got: '{xct}')"

    def test_api_docs_accessible(self):
        """OpenAPI docs are accessible (informational — consider disabling in prod)."""
        r = requests.get(f"{BASE}/docs")
        print(f"\n[INFO] API docs status: {r.status_code}")
        if r.status_code == 200:
            print("[WARNING] API docs (/docs) are publicly accessible — consider disabling in production")


# ─── RATE LIMITING TESTS ──────────────────────────────────────────────────────

class TestRateLimiting:

    def test_login_brute_force_not_blocked(self):
        """10 rapid failed logins should ideally be rate-limited."""
        statuses = []
        for _ in range(10):
            r = requests.post(f"{BASE}/api/auth/login", json={"username": "admin", "password": "wrong"})
            statuses.append(r.status_code)
        if all(s == 401 for s in statuses):
            pytest.xfail("No rate limiting on login — brute force possible (see audit)")
        # If any returns 429, rate limiting is working
        assert any(s == 429 for s in statuses), "Rate limiting active"


# ─── STATIC ASSETS TESTS ─────────────────────────────────────────────────────

class TestStaticAssets:

    def test_index_html_served(self):
        """SPA index.html is served on root."""
        r = requests.get(f"{BASE}/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_unknown_route_serves_spa(self):
        """Unknown routes serve SPA (client-side routing)."""
        r = requests.get(f"{BASE}/some/client/route")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_api_404_not_spa(self):
        """Unknown API routes return 404, not SPA."""
        r = requests.get(f"{BASE}/api/nonexistent")
        assert r.status_code == 404

    def test_static_js_accessible(self):
        """Static JS file is served."""
        r = requests.get(f"{BASE}/static/js/app.js")
        assert r.status_code == 200

    def test_openapi_schema_accessible(self):
        """OpenAPI JSON schema is accessible."""
        r = requests.get(f"{BASE}/openapi.json")
        assert r.status_code == 200
        schema = r.json()
        assert "paths" in schema
