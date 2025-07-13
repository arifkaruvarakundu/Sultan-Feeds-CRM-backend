# crm_backend/tasks/__init__.py
from crm_backend.celery_app import celery
from crm_backend.tasks.send_whatsapp import send_whatsapp_to_customers
from crm_backend.tasks.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_products import fetch_and_save_products
from crm_backend.database import SessionLocal
from celery import shared_task
from celery import chain

@celery.task(name="send_whatsapp_broadcast")
def send_whatsapp_broadcast():
    send_whatsapp_to_customers()


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

@shared_task(name="fetch_products_then_orders_task")
def fetch_products_then_orders_task():
    return chain(
        fetch_products_task.s(),
        fetch_orders_task.s()
    )()
