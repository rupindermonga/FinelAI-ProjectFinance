"""
Invoice Processing Worker — runs as its own systemd service.

Completely independent of the web server. Polls the DB every 10 seconds
for invoices in 'error' status and processes them one at a time with a
15-second gap (paid Gemini key rate-limit protection).

Never crashes when the web server restarts. Survives indefinitely.
"""
import os, sys, asyncio, logging, time

# Force SQLite path — Doppler may inject a postgres URL but this worker
# always uses the local DB directly. os.environ[] overrides Doppler.
db_url = os.environ.get("DATABASE_URL", "")
if not db_url or db_url.startswith("postgres"):
    os.environ["DATABASE_URL"] = "sqlite:////var/lib/finel-pf/db/project_finance.db"
# SQLAlchemy 1.4+ requires 'postgresql://' not 'postgres://'
elif db_url.startswith("postgres://"):
    os.environ["DATABASE_URL"] = db_url.replace("postgres://", "postgresql://", 1)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [worker] %(levelname)s %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("invoice-worker")

POLL_INTERVAL = 10    # seconds between idle polls
GAP_BETWEEN   = 15    # seconds between invoices (rate-limit buffer)


async def run():
    from app.database import SessionLocal
    from app.services.extractor import process_invoice_file
    from sqlalchemy import text

    processing_store: dict = {}
    logger.info("Worker started. Polling every %ds for invoices to process.", POLL_INTERVAL)

    while True:
        db = SessionLocal()
        try:
            row = db.execute(text(
                "SELECT id, source_file, user_id FROM invoices "
                "WHERE status='error' AND source_file IS NOT NULL "
                "ORDER BY id LIMIT 1"
            )).fetchone()

            if not row:
                db.close()
                await asyncio.sleep(POLL_INTERVAL)
                continue

            inv_id, src_file, user_id = row[0], row[1], row[2]

            if not os.path.isfile(src_file):
                db.execute(text(
                    "UPDATE invoices SET status='error', error_message='Source file missing' WHERE id=:id"
                ), {"id": inv_id})
                db.commit()
                db.close()
                continue

            # Claim the invoice: mark pending so no other worker picks it
            db.execute(text("UPDATE invoices SET status='pending' WHERE id=:id"), {"id": inv_id})
            db.commit()
            db.close()
            db = None

            logger.info("Processing invoice id=%s file=%s", inv_id, os.path.basename(src_file))
            fresh_db = SessionLocal()
            try:
                await process_invoice_file(inv_id, src_file, user_id, fresh_db, processing_store)
                logger.info("Invoice %s done.", inv_id)
            except Exception as exc:
                logger.error("Invoice %s failed: %s", inv_id, exc)
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
