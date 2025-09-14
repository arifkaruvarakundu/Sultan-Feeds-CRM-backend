import os
import datetime
import pandas as pd
import requests
import re
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from crm_backend.database import get_db
from crm_backend.customers.operation_helper import function_get_dead_customers
from datetime import datetime

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

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

def send_whatsapp_dead_customer_message(phone_number: str, customer_name: str, language: str = "en"):
    """
    Send WhatsApp template message to a dead customer.

    Args:
        phone_number (str): Customer phone number in international format.
        customer_name (str): Name of the customer.
        language (str): "en" or "ar".
    """
    template_config = {
        "en": {
            "template_name": "dead_customers_message",
            "language_code": "en",
        },
        "ar": {
            "template_name": "dead_customer_message_ar",
            "language_code": "ar",
        },
    }

    config = template_config.get(language)
    if not config:
        raise ValueError("Unsupported language. Use 'en' or 'ar'.")

    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
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
                    ],
                }
            ],
        },
    }

    response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
    return response.status_code, response.json()

def helper_function_to_sending_message_to_dead_customers(db: Session, language: str = "en"):
    """
    Fetch dead customers and send them WhatsApp messages.
    Ensures phone numbers are formatted to Kuwait standard before sending.
    Skips customers with invalid or missing numbers.
    """
    dead_customers = function_get_dead_customers(db)
    results = []

    print(f"🚀 Starting dead customer messaging at {datetime.now()} | Found {len(dead_customers)} customers")

    for customer in dead_customers:
        raw_phone = customer.get("phone")

        if not raw_phone:
            status = "Failed - No phone"
            print(f"❌ Customer {customer['customer_id']} ({customer.get('customer_name')}) → {status}")
            results.append({
                "customer_id": customer["customer_id"],
                "status": "Failed - No phone"
            })
            continue

        # Format and validate phone
        phone = format_kuwait_number(raw_phone)
        if not phone or len(phone) != 11 or not phone.startswith("965"):
            results.append({
                "customer_id": customer["customer_id"],
                "status": f"Failed - Invalid phone '{raw_phone}' → '{phone}'"
            })
            continue

        try:
            status_code, resp = send_whatsapp_dead_customer_message(
                phone_number=phone,
                customer_name=customer["customer_name"],
                language=language,
            )

            if status_code == 200:
                status = "✅ Success"
            else:
                status = f"Failed - {resp}"
            print(f"📩 Sent to {customer['customer_id']} ({customer['customer_name']}) | {phone} → {status}")   
            results.append({
                "customer_id": customer["customer_id"],
                "status": "Success" if status_code == 200 else f"Failed - {resp}"
            })
        except Exception as e:
            status = f"❌ Failed - {str(e)}"
            print(f"⚠️ Error sending to {customer['customer_id']} ({customer.get('customer_name')}) → {status}")
            results.append({
                "customer_id": customer["customer_id"],
                "status": f"Failed - {str(e)}"
            })
    print(f"🏁 Finished messaging {len(dead_customers)} customers at {datetime.now()}")
    return results