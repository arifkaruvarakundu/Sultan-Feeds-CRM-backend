from prophet import Prophet
import pandas as pd

# === Forecasting Function ===
def forecast_next_month_sales(df_orders, product_id):
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

    # Prepare result table
    forecast_30d['ds'] = forecast_30d['ds'].dt.date
    result = forecast_30d.rename(columns={
        'ds': 'date',
        'yhat': 'forecasted_units',
        'yhat_lower': 'lower_bound',
        'yhat_upper': 'upper_bound'
    })

    # print("\n📈 30-Day Forecast:")
    # print(result.head())

    return result

def forecast_customer_purchases(df_orders, customer_id):
    forecasts = []

    # print(">>> Starting forecast for customer:", customer_id)
    # print(">>> Total products ordered:", df_orders['product_id'].nunique())

    # Group by product
    for product_id, group in df_orders.groupby("product_id"):
        group["order_date"] = pd.to_datetime(group["order_date"])
        group["order_week"] = group["order_date"].dt.to_period("W").apply(lambda r: r.start_time)
        product_demand = group.groupby("order_week")["quantity"].sum().reset_index()
        product_demand.columns = ["ds", "y"]

        product_name = group["product_name"].iloc[0]  # ✅ fix here

        # print(f"Product {product_id} has {product_demand.shape[0]} weeks of data")

        if product_demand.shape[0] < 3:
            # print(f"⚠️ Skipping product {product_id}: not enough weekly data")
            continue

        model = Prophet()
        model.fit(product_demand)

        future = model.make_future_dataframe(periods=8, freq='W')  # 4 future weeks
        forecast = model.predict(future)

        forecast_weeks = forecast[forecast['ds'] > pd.to_datetime("today")][['ds', 'yhat', 'yhat_lower', 'yhat_upper']].copy()
        forecast_weeks['ds'] = forecast_weeks['ds'].dt.date

        forecast_weeks = forecast_weeks.rename(columns={
            'ds': 'date',
            'yhat': 'forecasted_units',
            'yhat_lower': 'lower_bound',
            'yhat_upper': 'upper_bound'
        })

        forecast_weeks["product_id"] = product_id
        forecast_weeks["product_name"] = product_name
        forecast_weeks["customer_id"] = customer_id

        forecasts.append(forecast_weeks)

    if not forecasts:
        return None

    return pd.concat(forecasts, ignore_index=True)







