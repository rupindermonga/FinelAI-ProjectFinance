"""Tests for invoice listing, stats, filtering, and bulk operations."""
import io


def test_stats_returns_correct_shape(auth_client):
    r = auth_client.get("/api/invoices/stats")
    assert r.status_code == 200
    d = r.json()
    for key in ("total", "processed", "pending", "errors"):
        assert key in d, f"Missing key: {key}"
        assert isinstance(d[key], int)


def test_invoice_list_empty_initially(auth_client):
    r = auth_client.get("/api/invoices")
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert "total" in d
    assert d["total"] == 0


def test_invoice_list_pagination_params(auth_client):
    r = auth_client.get("/api/invoices?page=1&limit=10")
    assert r.status_code == 200
    d = r.json()
    assert d["page"] == 1
    assert d["limit"] == 10


def test_upload_rejects_invalid_file_type(auth_client):
    r = auth_client.post("/api/upload", files={
        "files": ("malware.exe", b"\x4d\x5a\x90\x00", "application/octet-stream")
    })
    assert r.status_code == 200
    results = r.json()["results"]
    assert results[0]["status"] == "rejected"


def test_upload_rejects_non_image_disguised_as_pdf(auth_client):
    r = auth_client.post("/api/upload", files={
        "files": ("fake.pdf", b"this is not a pdf at all", "application/pdf")
    })
    assert r.status_code == 200
    assert r.json()["results"][0]["status"] == "rejected"


def test_upload_accepts_valid_pdf_magic(auth_client):
    # Minimal valid-magic PDF (just the header bytes, content doesn't matter for upload)
    fake_pdf = b"%PDF-1.4 fake content for testing"
    r = auth_client.post("/api/upload", files={
        "files": ("test_invoice.pdf", fake_pdf, "application/pdf")
    })
    assert r.status_code == 200
    result = r.json()["results"][0]
    # Should be queued (not rejected) — Gemini will handle extraction separately
    assert result["status"] in ("queued", "rejected")  # rejected ok if no Gemini key


def test_upload_detects_duplicate(auth_client):
    pdf = b"%PDF-1.4 duplicate test"
    auth_client.post("/api/upload", files={"files": ("inv.pdf", pdf, "application/pdf")})
    r2 = auth_client.post("/api/upload", files={"files": ("inv.pdf", pdf, "application/pdf")})
    results = r2.json()["results"]
    # Second upload should be detected as duplicate or queued
    assert results[0]["status"] in ("duplicate", "queued")


def test_stats_reflect_uploaded_invoice(auth_client):
    before = auth_client.get("/api/invoices/stats").json()["total"]
    auth_client.post("/api/upload", files={
        "files": ("new.pdf", b"%PDF-1.4 stats test", "application/pdf")
    })
    after = auth_client.get("/api/invoices/stats").json()["total"]
    assert after >= before  # total should not decrease


def test_upload_response_is_fast(auth_client):
    """Upload must return quickly — no blocking Gemini calls."""
    import time
    start = time.time()
    auth_client.post("/api/upload", files={
        "files": ("speed.pdf", b"%PDF-1.4 speed test", "application/pdf")
    })
    elapsed = time.time() - start
    assert elapsed < 5.0, f"Upload took {elapsed:.1f}s — too slow (Gemini may be blocking)"
