import pandas as pd
from prophet import Prophet
from sqlalchemy import create_engine
from collections import defaultdict
from crm_backend.tasks.reorder_messaging import send_whatsapp_reorder_reminder
from datetime import date
from dotenv import load_dotenv
import os
from crm_backend.models import Customer
from sqlalchemy.orm import sessionmaker

load_dotenv()

# Connect to your database
engine = create_engine(os.getenv("DATABASE_URL"))

# Reuse the same engine
SessionLocal = sessionmaker(bind=engine)

def get_customer_info(customer_id):
    session = SessionLocal()
    try:
        customer = session.query(Customer).filter_by(id=customer_id).first()
        return customer
    finally:
        session.close()

# Fetch orders
orders_df = pd.read_sql("SELECT customer_id, created_at FROM orders", engine)

# Convert to datetime
orders_df["created_at"] = pd.to_datetime(orders_df["created_at"])

customer_forecasts = defaultdict(list)
period_days = 30

# Loop over each customer
for customer_id, group in orders_df.groupby("customer_id"):
    order_dates = group["created_at"].sort_values()
    
    if len(order_dates) < 3:
        continue  # not enough history to train
    
    df = pd.DataFrame({
        "ds": order_dates,
        "y": [1] * len(order_dates)
    })
    
    model = Prophet()
    model.fit(df)
    
    future = model.make_future_dataframe(periods=period_days)
    forecast = model.predict(future)
    
    # Filter to only future dates
    future_forecast = forecast[forecast["ds"] > order_dates.max()]
    
    # Select dates with high reorder probability
    likely_reorder = future_forecast[future_forecast["yhat"] > 0.5]  # Tune threshold
    
    for _, row in likely_reorder.iterrows():
        customer_forecasts[customer_id].append(row["ds"].date())


today = date.today()

for customer_id, predicted_dates in customer_forecasts.items():
    if today in predicted_dates:
        customer = get_customer_info(customer_id)  # Your function
        full_name = f"{customer.first_name} {customer.last_name}"
        
        send_whatsapp_reorder_reminder(
            phone_number=customer.phone,
            customer_name=full_name
        )