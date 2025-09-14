import os
import datetime
import pandas as pd
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from crm_backend.database import get_db
from crm_backend.customers.operation_helper import function_get_customers_with_low_churnRisk
from crm_backend.AI.db_helper import fetch_order_data
from crm_backend.AI.operation_helper import forecast_customer_purchases

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{PHONE_NUMBER_ID}/messages"

# TEMPLATE_NAME = "product_forecast_offer"
# LANGUAGE_CODE = "en_US"

def helper_function_to_sending_message_to_low_churn_risk_customers(db: Session):
    low_churn_customers = function_get_customers_with_low_churnRisk(db)
    all_forecasts = []

    for customer in low_churn_customers:
        customer_id = customer["customer_id"]
        df_orders = fetch_order_data(db, customer_id)

        forecast_df = forecast_customer_purchases(df_orders, customer_id)
        if forecast_df is not None:
            # Merge customer info so we can send later without re-fetching
            forecast_df["customer_name"] = customer["customer_name"]
            forecast_df["phone"] = customer["phone"]
            all_forecasts.append(forecast_df)

    if not all_forecasts:
        return pd.DataFrame()  # Empty DataFrame

    all_forecasts_df = pd.concat(all_forecasts, ignore_index=True)
    today = datetime.date.today()
    todays_forecasts = all_forecasts_df[all_forecasts_df['date'] == today]

    return todays_forecasts

def send_whatsapp_forecast_message(phone_number: str, customer_name: str, language: str = "en"):
    
    template_config = {
        "en": {
            "template_name": "example_for_quick_reply",
            "language_code": "en_US",
        },
        "ar": {
            "template_name": "order_management_1",
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
                    "parameters": [{"type": "text", "text": customer_name}],
                }
            ],
        },
    }

    response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
    return response.status_code, response.json()

