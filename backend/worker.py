"""
Invoice Processing Worker — runs as its own systemd service.

Completely independent of the web server. Polls the DB every 10 seconds
for invoices in 'error' status and processes them one at a time.
Writes a heartbeat row every 30s so the health dashboard can detect stalls.
"""
import os, sys, asyncio, logging, time

db_url = os.environ.get("DATABASE_URL", "")
if not db_url or db_url.startswith("postgres"):
    os.environ["DATABASE_URL"] = "sqlite:////var/lib/finel-pf/db/project_finance.db"
elif db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgres://", "postgresql://", 1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("invoice-worker")

POLL_INTERVAL  = 10   # seconds between idle polls
GAP_BETWEEN    = 5    # seconds between invoices
HEARTBEAT_SECS = 30   # write heartbeat every N seconds
MAX_RETRIES    = 4    # give up after this many attempts


async def run():
    from app.database import SessionLocal
    from app.services.extractor import process_invoice_file
    from sqlalchemy import text

    processing_store: dict = {}
    processed_session = 0
    last_heartbeat = 0.0
    pid = os.getpid()

    logger.info("Worker started (pid=%s). Polling every %ds.", pid, POLL_INTERVAL)

    # On startup: reset any orphaned 'processing' or 'pending' invoices back to 'error'
    # so this worker (or a previous crashed one) doesn't leave invoices permanently stuck.
    startup_db = SessionLocal()
    try:
        orphaned = startup_db.execute(text(
            "SELECT COUNT(*) FROM invoices WHERE status IN ('processing', 'pending') AND source_file IS NOT NULL"
        )).fetchone()[0]
        if orphaned:
            startup_db.execute(text(
                "UPDATE invoices SET status='error', error_message='Re-queued after worker restart' "
                "WHERE status IN ('processing', 'pending') AND source_file IS NOT NULL"
            ))
            startup_db.commit()
            logger.info("Reset %d orphaned invoices to 'error' for reprocessing.", orphaned)
    finally:
        startup_db.close()

    while True:
        db = SessionLocal()
        try:
            # ── Heartbeat ──────────────────────────────────────────
            now = time.time()
            if now - last_heartbeat >= HEARTBEAT_SECS:
                queue_depth = db.execute(text(
                    "SELECT COUNT(*) FROM invoices WHERE status='error' "
                    "AND COALESCE(retry_count,0) < :max"
                ), {"max": MAX_RETRIES}).fetchone()[0]
                db.execute(text(
                    "INSERT INTO worker_heartbeats (ts, queue_depth, processed_session, worker_pid) "
                    "VALUES (CURRENT_TIMESTAMP, :q, :p, :pid)"
                ), {"q": queue_depth, "p": processed_session, "pid": pid})
                # Keep only last 200 heartbeat rows
                db.execute(text(
                    "DELETE FROM worker_heartbeats WHERE id NOT IN ("
                    "  SELECT id FROM worker_heartbeats ORDER BY id DESC LIMIT 200)"
                ))
                db.commit()
                last_heartbeat = now

            # ── Pick next invoice ───────────────────────────────────
            row = db.execute(text(
                "SELECT id, source_file, user_id, COALESCE(retry_count,0) FROM invoices "
                "WHERE status='error' AND source_file IS NOT NULL "
                "AND COALESCE(retry_count,0) < :max "
                "ORDER BY id LIMIT 1"
            ), {"max": MAX_RETRIES}).fetchone()

            if not row:
                db.close()
                await asyncio.sleep(POLL_INTERVAL)
                continue

            inv_id, src_file, user_id, retry_count = row[0], row[1], row[2], row[3]

            if not os.path.isfile(src_file):
                db.execute(text(
                    "UPDATE invoices SET status='error', error_message='Source file missing' WHERE id=:id"
                ), {"id": inv_id})
                db.commit()
                db.close()
                continue

            # Claim — atomic status change prevents double-processing
            db.execute(text(
                "UPDATE invoices SET status='processing', retry_count=COALESCE(retry_count,0)+1 WHERE id=:id"
            ), {"id": inv_id})
            db.commit()
            db.close()
            db = None

            attempt = retry_count + 1
            logger.info("Processing invoice id=%s file=%s (attempt %s/%s)",
                        inv_id, os.path.basename(src_file), attempt, MAX_RETRIES)

            fresh_db = SessionLocal()
            try:
                await asyncio.wait_for(
                    process_invoice_file(inv_id, src_file, user_id, fresh_db, processing_store),
                    timeout=180  # 3 minutes hard limit per invoice
                )
                processed_session += 1
                logger.info("Invoice %s done. Session total: %s", inv_id, processed_session)
            except asyncio.TimeoutError:
                logger.error("Invoice %s TIMED OUT after 180s — marking error.", inv_id)
            except Exception as exc:
                logger.error("Invoice %s failed (attempt %s): %s", inv_id, attempt, exc)
                if attempt >= MAX_RETRIES:
                    logger.warning("Invoice %s reached max retries — permanently errored.", inv_id)
            finally:
                fresh_db.close()

            await asyncio.sleep(GAP_BETWEEN)

        except Exception as exc:
            logger.error("Worker loop error: %s", exc)
            if db:
                db.close()
            await asyncio.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    asyncio.run(run())
