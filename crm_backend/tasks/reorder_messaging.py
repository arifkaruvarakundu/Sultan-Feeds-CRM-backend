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
from datetime import date, timedelta
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

#using prophet

# def predict_customers_to_remind(period_days: int = 30):
#     """
#     Predicts which customers are likely to reorder today.
#     Returns a list of customer IDs.
#     """
#     orders_df = pd.read_sql("SELECT customer_id, created_at FROM orders", engine)
#     print("orders_df:", orders_df)
#     orders_df["created_at"] = pd.to_datetime(orders_df["created_at"])

#     customer_forecasts = defaultdict(list)
#     today = date.today()

#     for customer_id, group in orders_df.groupby("customer_id"):
#         order_dates = group["created_at"].sort_values()

#         if len(order_dates) < 3:
#             continue

#         df = pd.DataFrame({
#             "ds": order_dates,
#             "y": [1] * len(order_dates)
#         })
#         print("df in predict:",df)
#         model = Prophet()
#         model.fit(df)

#         future = model.make_future_dataframe(periods=period_days)
#         forecast = model.predict(future)

#         future_forecast = forecast[forecast["ds"] > order_dates.max()]

#         likely_reorder = future_forecast[future_forecast["yhat"] > 0.5]

#         for _, row in likely_reorder.iterrows():
#             if row["ds"].date() == today:
#                 customer_forecasts[customer_id].append(today)

#         # # Get the most likely reorder date (highest prediction)
#         # best_day = future_forecast.loc[future_forecast['yhat'].idxmax()]
#         # predicted_date = best_day["ds"].date()

#         # Remind only if that predicted date is exactly today
#         if predicted_date == today:
#             customer_forecasts[customer_id].append(today)

#     print(f"🔮 Predicted {len(customer_forecasts)} customers to remind today.")
#     return list(customer_forecasts.keys())

#using Avearage gap prediction(AGP)

def predict_customers_to_remind(df, orders_df, target_date=None, last_reminded=None):
    """
    Predict customers to remind based on:
    - Classification
    - Churn risk
    - Classification-based cooldown periods
    """
    today = target_date or date.today()
    reminders = []
    last_reminded = last_reminded or {}

    # Define cooldown days for each classification
    cooldown_days_map = {
        "Loyal": 14,
        "Frequent": 10,
    }

    for _, row in df.iterrows():
        customer_id = row["customer_id"]
        classification = row["classification"]
        churn_risk = row["churn_risk"]
        last_order_date = pd.to_datetime(row["last_order_date"]) if row["last_order_date"] else None

        # Skip high churn or dead/no orders
        if churn_risk == "High" or classification in ["Dead", "No Orders"]:
            continue

        # Loyal / Frequent → average reorder interval
        if classification in ["Loyal", "Frequent"]:
            # Check cooldown
            cooldown_days = cooldown_days_map.get(classification, 7)  # default 7 if not listed
            if customer_id in last_reminded:
                if (today - last_reminded[customer_id]).days < cooldown_days:
                    continue

            customer_orders = orders_df[orders_df["customer_id"] == customer_id]["created_at"].sort_values()
            if len(customer_orders) < 2:
                continue
            gaps = customer_orders.diff().dropna().dt.days
            avg_gap = gaps.mean()
            predicted_next = customer_orders.max().date() + timedelta(days=round(avg_gap))
            if predicted_next == today:
                reminders.append(customer_id)
        else:
            continue

    # Update last reminder date
    for cid in reminders:
        last_reminded[cid] = today

    print(f"📣 {len(reminders)} customers to remind on {today}")
    return reminders, last_reminded

def send_reorder_reminders_to_customers(customer_ids: list):
    """
    Sends both English and Arabic WhatsApp reorder reminders to the given customer IDs.
    """
    for customer_id in customer_ids:
        customer = get_customer_info(customer_id)
        if not customer or not customer.phone:
            print(f"⚠️ Skipping customer {customer_id}: No phone number.")
            continue

        full_name = f"{customer.first_name} {customer.last_name}".strip()
        phone_number = format_kuwait_number(customer.phone)

        # Validate after formatting
        if not phone_number or len(phone_number) != 11 or not phone_number.startswith("965"):
            print(f"❌ Skipping {full_name} (ID: {customer_id}): Invalid Kuwait phone number '{customer.phone}' → '{phone_number}'")
            continue

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