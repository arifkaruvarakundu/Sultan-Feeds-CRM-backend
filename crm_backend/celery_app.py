import os
from dotenv import load_dotenv
from celery import Celery
from celery.schedules import crontab

load_dotenv()

REDIS_BROKER_URL = os.getenv("REDIS_URL", "redis://:${REDIS_PASSWORD}@redis:6379/0")

celery = Celery(
    "crm_tasks",
    broker=REDIS_BROKER_URL,
    backend=REDIS_BROKER_URL,
    include=["crm_backend.tasks"],  # 👈 Ensures tasks are auto-discovered
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    beat_scheduler='celery.beat.PersistentScheduler',
)

celery.conf.beat_schedule = {
    # 🔁 Fetch WooCommerce orders every 15 minutes
    "fetch-orders-every-1-mins": {
        "task": "fetch_orders_task",
        "schedule": crontab(minute="*"),
    },

    # 🛒 Fetch WooCommerce products every 2 hours
    "fetch-products-every-2-hours": {
        "task": "fetch_products_task",
        "schedule": crontab(minute=0, hour="*/2"),
    },

    # 📲 Send WhatsApp messages daily at 10 AM (if re-enabled)
    # "send-whatsapp-daily": {
    #     "task": "send_whatsapp_broadcast",
    #     "schedule": crontab(hour=10, minute=0),
    # },

    # 🔁 Run reorder prediction and message customers daily at 9 AM UTC
    # "send-reorder-prediction-daily": {
    #     "task": "predict_customers_task",
    #     "schedule": crontab(hour=9, minute=0),
    # },

    # sending message after one month from the order date
      "send-whatsapp-after-one-month":{
        "task": "send_reminders_after_one_month_task",
        "schedule": crontab(hour=10, minute=0)
      },
      # sending message after one month from the order date
    #   "send-whatsapp-to-low-churn-customers":{
    #     "task": "send_forecast_messages_to_low_churn_task",
    #     "schedule": crontab(hour=10, minute=0)
    #   }
    
    # 📲 Send WhatsApp messages to DEAD customers once a month
    # "send-dead-customers-messages-monthly": {
    #     "task": "send_dead_customers_messages",
    #     "schedule": crontab(minute=0, hour=10, day_of_month="1"),
    # },

}

