from crm_backend.celery_app import celery
from crm_backend.tasks.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_products import fetch_and_save_products
from crm_backend.database import SessionLocal

@celery.task(name="fetch_orders_task")
def fetch_orders_task(*args, **kwargs):
    db = SessionLocal()
    try:
        fetch_and_save_orders(db)
    finally:
        db.close()

@celery.task(name="fetch_products_task")
def fetch_products_task(*args, **kwargs):
    db = SessionLocal()
    try:
        fetch_and_save_products(db)
    finally:
        db.close()


