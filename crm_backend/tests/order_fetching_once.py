# run_fetch_once.py
from crm_backend.database import SessionLocal
from crm_backend.tasks.fetch_orders import fetch_all_orders_once  # change to your filename

if __name__ == "__main__":
    db = SessionLocal()
    try:
        fetch_all_orders_once(db)
    finally:
        db.close()