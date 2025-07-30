import requests
from dotenv import load_dotenv
from crm_backend.database import SessionLocal
from crm_backend.models import Customer
# from crm_backend.tasks.reorder_messaging import send_whatsapp_reorder_reminder
from crm_backend.celery_app import celery
from sqlalchemy.orm import sessionmaker
from prophet import Prophet
from sqlalchemy import create_engine
from collections import defaultdict
from datetime import date
import pandas as pd
import os
import re
import time

load_dotenv()

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

def format_kuwait_number(raw: str) -> str:
    """
    Formats a raw phone number to Kuwait format.
    Example:
        - "0096598765432" → "96598765432"
        - "98765432" → "96598765432"
        - "096598765432" → "96598765432"
        - "96598765432" → "96598765432"
    """
    if not raw:
        return ""

    # Remove all non-digit characters
    digits = re.sub(r"\D", "", raw)

    # Remove leading zeros
    normalized = re.sub(r"^0+", "", digits)

    # If it starts with '965' and is 11 digits, return it
    if normalized.startswith("965") and len(normalized) == 11:
        return normalized

    # If it's 8 digits, assume it's a local Kuwait number and prepend '965'
    if len(normalized) == 8:
        return "965" + normalized

    # If it's longer than 8 digits, take last 8 digits and prepend '965'
    if len(normalized) > 8:
        return "965" + normalized[-8:]

    # Fallback: return as is
    return normalized

def send_whatsapp_reorder_reminder(phone_number: str, customer_name: str, language: str = "en"):
    """
    Sends a WhatsApp template message with quick replies in English or Arabic.
    """

    template_config = {
        "en": {
            "template_name": "example_for_quick_reply",
            "language_code": "en_US"
        },
        "ar": {
            "template_name": "order_management_1",
            "language_code": "ar"
        }
    }

    if language not in template_config:
        raise ValueError("Unsupported language. Use 'en' or 'ar'.")

    config = template_config[language]

    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    data = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": config["template_name"],
            "language": {"code": config["language_code"]},
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        {"type": "text", "text": customer_name}
                    ]
                }
            ]
        }
    }

    response = requests.post(WHATSAPP_API_URL, headers=headers, json=data)
    return response.json()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)

def get_customer_info(customer_id):
    session = SessionLocal()
    try:
        return session.query(Customer).filter_by(id=customer_id).first()
    finally:
        session.close()

def predict_customers_to_remind(period_days: int = 30):
    """
    Predicts which customers are likely to reorder today.
    Returns a list of customer IDs.
    """
    orders_df = pd.read_sql("SELECT customer_id, created_at FROM orders", engine)
    orders_df["created_at"] = pd.to_datetime(orders_df["created_at"])

    customer_forecasts = defaultdict(list)
    today = date.today()

    for customer_id, group in orders_df.groupby("customer_id"):
        order_dates = group["created_at"].sort_values()

        if len(order_dates) < 3:
            continue

        df = pd.DataFrame({
            "ds": order_dates,
            "y": [1] * len(order_dates)
        })

        model = Prophet()
        model.fit(df)

        future = model.make_future_dataframe(periods=period_days)
        forecast = model.predict(future)

        future_forecast = forecast[forecast["ds"] > order_dates.max()]
        likely_reorder = future_forecast[future_forecast["yhat"] > 0.5]

        for _, row in likely_reorder.iterrows():
            if row["ds"].date() == today:
                customer_forecasts[customer_id].append(today)
    print(f"🔮 Predicted {len(customer_forecasts)} customers to remind today.")
    return list(customer_forecasts.keys())

def send_reorder_reminders_to_customers(customer_ids: list):
    """
    Sends both English and Arabic WhatsApp reorder reminders to the given customer IDs.
    """
    for customer_id in customer_ids:
        customer = get_customer_info(customer_id)
        if customer and customer.phone:
            full_name = f"{customer.first_name} {customer.last_name}".strip()
            phone_number = customer.phone

            print(f"📤 Sending to {full_name} ({phone_number}) [ID: {customer_id}]")

            try:
                # Send English message
                send_whatsapp_reorder_reminder(
                    phone_number=phone_number,
                    customer_name=full_name,
                    language="en"
                )
                print(f"✅ English message sent to {phone_number}")
                time.sleep(1)
                # Send Arabic message
                send_whatsapp_reorder_reminder(
                    phone_number=phone_number,
                    customer_name=full_name,
                    language="ar"
                )
                print(f"✅ Arabic message sent to {phone_number}")

            except Exception as e:
                print(f"❌ Failed to send message(s) to {customer_id}: {e}")

def run_reorder_prediction_task():
    """
    Combines prediction and message sending.
    """
    customer_ids = predict_customers_to_remind()
    send_reorder_reminders_to_customers(customer_ids)
    print(f"✅ Processed reorder prediction for {len(customer_ids)} customers.")
    return f"Processed reorder prediction for {len(customer_ids)} customers."