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

TEMPLATE_NAME = "product_forecast_offer"
LANGUAGE_CODE = "en_US"

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

def send_to_low_churn_customers(todays_forecasts: pd.DataFrame):
    headers = {
        "Authorization": f"Bearer {ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    for _, row in todays_forecasts.iterrows():
        whatsapp_number = row["phone"]

        payload = {
            "messaging_product": "whatsapp",
            "to": whatsapp_number,
            "type": "template",
            "template": {
                "name": TEMPLATE_NAME,
                "language": { "code": LANGUAGE_CODE },
                "components": [
                    {
                        "type": "body",
                        "parameters": [
                            { "type": "text", "text": row["customer_name"] },
                            { "type": "text", "text": row["product_name"] },
                            { "type": "text", "text": "10" }
                        ]
                    }
                ]
            }
        }

        response = requests.post(WHATSAPP_API_URL, headers=headers, json=payload)
        if response.status_code == 200:
            print(f"✅ Sent template to {row['customer_name']} ({whatsapp_number})")
        else:
            print(f"❌ Failed for {row['customer_name']}: {response.text}")

# if __name__ == "__main__":
#     db = next(get_db())
#     todays_forecasts = helper_function_to_sending_message_to_low_churn_risk_customers(db)
#     # if not todays_forecasts.empty:
#     #     send_to_low_churn_customers(todays_forecasts)
#     if not todays_forecasts.empty:
#         print("📋 Today's forecasted customers & products:")
#         for _, row in todays_forecasts.iterrows():
#             print(f"Customer: {row['customer_name']} | Product: {row['product_name']}")
#     else:
#         print("No forecasts to send today.")
