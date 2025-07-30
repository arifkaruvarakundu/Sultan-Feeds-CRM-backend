from crm_backend.celery_app import celery
from crm_backend.tasks.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_products import fetch_and_save_products
from crm_backend.database import SessionLocal
from crm_backend.tasks.reorder_messaging import predict_customers_to_remind, send_reorder_reminders_to_customers

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

# @celery.task(name="predict_customers_task")
# def predict_customers_task():
#     customer_ids = predict_customers_to_remind()
#     if customer_ids:
#         send_reminders_task.delay(customer_ids)

# @celery.task(name="send_reminders_task")
# def send_reminders_task(customer_ids: list):
#     send_reorder_reminders_to_customers(customer_ids)


