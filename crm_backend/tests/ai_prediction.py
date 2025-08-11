from prophet import Prophet
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from dotenv import load_dotenv
import os
from crm_backend.models import *  # Ensure your models are defined

# === Load environment variables ===
load_dotenv()

# === Setup SQLAlchemy engine and session ===
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)
session = Session()

# === Fetch data from the DB ===
def fetch_order_data():
    query = (
        session.query(
            Customer.id.label("customer_id"),
            OrderItem.product_id.label("product_id"),
            Order.created_at.label("order_date"),
            OrderItem.quantity.label("quantity"),
            OrderItem.price.label("price")
        )
        .join(Order, Customer.id == Order.customer_id)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= '2024-01-01')  # You can change this date as needed
    )

    df = pd.read_sql(query.statement, session.bind)
    return df

# === Forecasting Function ===
def forecast_next_month_sales(df_orders, product_id):
    import os  # Ensure import is available

    # Filter for specific product
    product_df = df_orders[df_orders['product_id'] == product_id]
    product_demand = product_df.groupby("order_date")["quantity"].sum().reset_index()

    if product_demand.shape[0] < 10:
        print(f"Skipping Product ID {product_id}: not enough data.")
        return None

    product_demand.columns = ["ds", "y"]  # Prophet expects 'ds' and 'y'

    # Train model
    model = Prophet()
    model.fit(product_demand)

    # Forecast next 30 days
    future = model.make_future_dataframe(periods=30)
    forecast = model.predict(future)

    # Filter forecast for next 30 days only
    today = pd.to_datetime("today").normalize()
    forecast_30d = forecast[forecast['ds'] > today][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()

    # === Ensure output folder exists ===
    output_dir = "outputs"
    os.makedirs(output_dir, exist_ok=True)

    # === Plot ===
    fig, ax = plt.subplots(figsize=(12, 6))
    model.plot(forecast, ax=ax)
    ax.axvline(x=today, color='red', linestyle='--', label='Today')
    ax.set_title(f"30-Day Forecast for Product ID {product_id}", fontsize=14)
    ax.set_xlabel("Date")
    ax.set_ylabel("Units Sold")
    ax.legend()
    plot_path = os.path.join(output_dir, f"forecast_30d_product_{product_id}.png")
    plt.savefig(plot_path)
    plt.close()
    print(f"✅ Plot saved: {plot_path}")

    # === Prepare result table ===
    forecast_30d['ds'] = forecast_30d['ds'].dt.date
    result = forecast_30d.rename(columns={
        'ds': 'date',
        'yhat': 'forecasted_units',
        'yhat_lower': 'lower_bound',
        'yhat_upper': 'upper_bound'
    })

    print("\n📈 30-Day Forecast:")
    print(result.head())

    # === Save to Excel in output directory ===
    excel_path = os.path.join(output_dir, f"forecast_30d_product_{product_id}.xlsx")
    result.to_excel(excel_path, index=False)
    print(f"📄 Excel saved: {excel_path}")

    return result


# === Main Execution ===
if __name__ == "__main__":
    df_orders = fetch_order_data()
    forecast_next_month_sales(df_orders, product_id=16819)
