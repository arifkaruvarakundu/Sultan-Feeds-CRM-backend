# celery_app.py
import os
from dotenv import load_dotenv
from celery import Celery
from celery.schedules import crontab

load_dotenv()

REDIS_BROKER_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

celery = Celery(
    "crm_tasks",
    broker=REDIS_BROKER_URL,
    backend=REDIS_BROKER_URL,
    include=["crm_backend.tasks"],  # 👈 Ensures periodic task is discoverable
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_scheduler='celery.beat.PersistentScheduler',  # optional but recommended
)

# # ⏰ Periodic Tasks
# celery.conf.beat_schedule = {
#     # 🔁 Fetch WooCommerce orders every 15 minutes
#     "fetch-orders-every-15-mins": {
#         "task": "fetch_orders_task",  # Uses name from @celery.task(name="...")
#         "schedule": crontab(minute="*/15"),
#     },
    
#     # 📲 Send WhatsApp messages every day at 10 AM (example)
#     "send-whatsapp-daily": {
#         "task": "send_whatsapp_broadcast",
#         "schedule": crontab(hour=10, minute=0),
#     },
#     "fetch-products-every-120-mins": {
#         "task": "fetch_products_task",  # Uses name from @celery.task(name="...")
#         "schedule": crontab(minute="*/120"),
#     },
    
# }

celery.conf.beat_schedule = {
    "fetch-products-then-orders-every-15-mins": {
        "task": "fetch_products_then_orders_task",
        "schedule": crontab(minute="*/15"),
    },
    "send-whatsapp-daily": {
        "task": "send_whatsapp_broadcast",
        "schedule": crontab(hour=10, minute=0),
    },
}
