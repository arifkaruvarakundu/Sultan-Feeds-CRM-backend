from crm_backend.database import get_db
import requests
import os
from datetime import date
from dateutil.relativedelta import relativedelta
from sqlalchemy.orm import Session
from dotenv import load_dotenv
from sqlalchemy import text

load_dotenv()

def get_customers_since(db: Session):
    start_date = date(2025, 9, 1)

    query = text("""
        SELECT c.first_name, c.last_name, c.phone, o.created_at
        FROM orders o
        JOIN customers c ON o.customer_id = c.id
        WHERE o.created_at >= :start_date
    """)

    result = db.execute(query, {"start_date": start_date}).fetchall()

    return [
        {
            "customer_name": f"{row[0]} {row[1]}",
            "phone_number": row[2],
            "order_date": row[3]
        }
        for row in result
    ]

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

def send_whatsapp_reorder_reminder_after_one_month(phone_number: str, customer_name: str, language: str = "en"):
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

    config = template_config.get(language)
    if not config:
        raise ValueError("Unsupported language. Use 'en' or 'ar'.")

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
    return response.status_code, response.json()

def send_whatsapp_message_after_one_month(db: Session):
    
    today = date.today()
    customers = get_customers_since(db)

    for row in customers:
        customer_name = row["customer_name"]
        phone_number = row["phone_number"]
        order_date = row["order_date"]

        send_date = order_date + relativedelta(months=1)
        if send_date == today:
            # Send English
            status_en, result_en = send_whatsapp_reorder_reminder_after_one_month(
                phone_number, customer_name, "en"
            )
            print(f"[EN] Sent to {customer_name} ({phone_number}): {status_en} - {result_en}")

            # Send Arabic
            status_ar, result_ar = send_whatsapp_reorder_reminder_after_one_month(
                phone_number, customer_name, "ar"
            )
            print(f"[AR] Sent to {customer_name} ({phone_number}): {status_ar} - {result_ar}")