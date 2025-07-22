# crm_backend/scripts/backfill_orders.py

from crm_backend.database import SessionLocal
from crm_backend.tasks.fetch_orders import backfill_existing_orders

if __name__ == "__main__":
    print("🚀 Starting backfill...")
    db = SessionLocal()
    try:
        backfill_existing_orders(db)
    finally:
        db.close()
    print("✅ Backfill completed.")
