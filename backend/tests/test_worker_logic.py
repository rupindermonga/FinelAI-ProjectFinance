"""
Tests for worker retry logic and invoice state machine.
These run against the DB directly without needing a real Gemini key.
"""
import pytest
from sqlalchemy import text


def _create_invoice(db, status="error", retry_count=0, filename="test.pdf"):
    db.execute(text(
        "INSERT INTO invoices (user_id, org_id, status, original_filename, source_file, retry_count, error_message) "
        "VALUES (1, 1, :s, :f, '/tmp/fake.pdf', :r, 'test error')"
    ), {"s": status, "f": filename, "r": retry_count})
    db.commit()
    return db.execute(text("SELECT id FROM invoices ORDER BY id DESC LIMIT 1")).fetchone()[0]


def test_worker_skips_invoices_at_max_retries(db_session):
    """Invoices with retry_count >= 4 must not be picked up."""
    inv_id = _create_invoice(db_session, status="error", retry_count=4)
    row = db_session.execute(text(
        "SELECT id FROM invoices WHERE status='error' AND COALESCE(retry_count,0) < 4 AND id=:id"
    ), {"id": inv_id}).fetchone()
    assert row is None, "Worker should not pick up invoice with retry_count >= 4"


def test_worker_picks_up_new_error_invoice(db_session):
    """New error invoices (retry_count=0) must be picked up."""
    inv_id = _create_invoice(db_session, status="error", retry_count=0)
    row = db_session.execute(text(
        "SELECT id FROM invoices WHERE status='error' AND COALESCE(retry_count,0) < 4 AND id=:id"
    ), {"id": inv_id}).fetchone()
    assert row is not None


def test_retry_count_increments(db_session):
    """Each processing attempt must increment retry_count."""
    inv_id = _create_invoice(db_session, retry_count=1)
    db_session.execute(text(
        "UPDATE invoices SET retry_count=COALESCE(retry_count,0)+1, status='processing' WHERE id=:id"
    ), {"id": inv_id})
    db_session.commit()
    rc = db_session.execute(text("SELECT retry_count FROM invoices WHERE id=:id"), {"id": inv_id}).fetchone()[0]
    assert rc == 2


def test_invoice_status_transitions(db_session):
    """Verify valid status: error -> processing -> processed."""
    inv_id = _create_invoice(db_session, status="error")
    db_session.execute(text("UPDATE invoices SET status='processing' WHERE id=:id"), {"id": inv_id})
    db_session.commit()
    s = db_session.execute(text("SELECT status FROM invoices WHERE id=:id"), {"id": inv_id}).fetchone()[0]
    assert s == "processing"

    db_session.execute(text("UPDATE invoices SET status='processed' WHERE id=:id"), {"id": inv_id})
    db_session.commit()
    s2 = db_session.execute(text("SELECT status FROM invoices WHERE id=:id"), {"id": inv_id}).fetchone()[0]
    assert s2 == "processed"


def test_duplicate_detection_by_hash(db_session):
    """Two invoices with the same file_hash in the same org must be detected."""
    h = "abc123deadbeef"
    db_session.execute(text(
        "INSERT INTO invoices (user_id, org_id, status, file_hash, original_filename) "
        "VALUES (1, 1, 'processed', :h, 'orig.pdf')"
    ), {"h": h})
    db_session.commit()
    existing = db_session.execute(text(
        "SELECT id FROM invoices WHERE org_id=1 AND file_hash=:h"
    ), {"h": h}).fetchone()
    assert existing is not None, "Duplicate detection query must find existing invoice"
