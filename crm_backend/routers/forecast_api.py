from fastapi import APIRouter
from fastapi.responses import JSONResponse
from crm_backend.AI.db_helper import fetch_order_data, fetch_customer_order_data
from crm_backend.AI.operation_helper import forecast_next_month_sales, forecast_customer_purchases
import pandas as pd
import numpy as np

router = APIRouter()

@router.get("/forecast/product/{product_id}")
def get_forecast(product_id: int):
    df_orders = fetch_order_data()
    result = forecast_next_month_sales(df_orders, product_id)

    if result is None:
        return JSONResponse(status_code=404, content={"message": "Not enough data for forecast"})

    # Convert DataFrame to list of dicts for frontend
    forecast_data = result.to_dict(orient="records")
    return {"product_id": product_id, "forecast": forecast_data}

# @router.get("/forecast/customer/{customer_id}")
# def get_customer_forecast(customer_id: int):

#     df_orders = fetch_customer_order_data(customer_id)
  
#     if df_orders.empty:
#         return JSONResponse(status_code=404, content={"message": "No order history for this customer"})

#     result = forecast_customer_purchases(df_orders, customer_id)

#     if result is None:
#         return JSONResponse(status_code=404, content={"message": "Not enough data to generate forecasts"})

#     return {"customer_id": customer_id, "forecasts": result.to_dict(orient="records")}

@router.get("/forecast/customer-with-offer/{customer_id}", tags=["Forecast"])
def get_customer_forecast_with_offer(customer_id: int):

    df_orders = fetch_customer_order_data(customer_id)

    if df_orders.empty:
        return JSONResponse(
            status_code=404, 
            content={"message": "No order history for this customer"}
        )

    result = forecast_customer_purchases(df_orders, customer_id)

    if result is None:
        return JSONResponse(
            status_code=404, 
            content={"message": "Not enough data to generate forecasts"}
        )

    # Step 1: Ensure correct date format
    result["date"] = pd.to_datetime(result["date"])
    result = result.sort_values(["product_id", "date"])

    # Step 2: Compute extra features (per product per customer)
    result["previous_week_units"] = result.groupby("product_id")["forecasted_units"].shift(1)
    result["week_of_year"] = result["date"].dt.isocalendar().week
    result["uncertainty"] = result["upper_bound"] - result["lower_bound"]
    result["cv"] = result["uncertainty"] / result["forecasted_units"]

    # Step 3: Rule-based offer suggestion
    def label_offer(row):
        if row["forecasted_units"] < 5:
            return "Win-back Offer"  # very low purchase prediction → try to re-engage
        elif 5 <= row["forecasted_units"] < 10:
            if row["cv"] > 1.0:
                return "Moderate Discount"
            else:
                return "Loyalty Discount"
        elif row["forecasted_units"] >= 10:
            if row["cv"] > 1.0:
                return "Exclusive Product Teaser"  # high uncertainty but high demand
            else:
                return "No Offer"
        else:
            return "No Offer"

    result["offer_applied"] = result.apply(label_offer, axis=1)

    # Step 4: Output formatting
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")
    result = result.replace({np.nan: None, np.inf: None, -np.inf: None})

    return result.to_dict(orient="records")

@router.get("/forecast-with-offer/{product_id}", tags=["Forecast"])
def forecasting_with_offer(product_id:int):
    forecast_data = get_forecast(product_id)

    # Step 1: Load data into DataFrame
    df = pd.DataFrame(forecast_data["forecast"])
    df["product_id"] = forecast_data["product_id"]
    df["date"] = pd.to_datetime(df["date"])

    # Step 2: Compute additional features
    df = df.sort_values("date")
    df["previous_day_units"] = df["forecasted_units"].shift(1)
    df["day_of_week"] = df["date"].dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6]).astype(int)
    df["uncertainty"] = df["upper_bound"] - df["lower_bound"]
    df["cv"] = df["uncertainty"] / df["forecasted_units"]

    # Step 3: Apply rule-based labeling
    def label_offer(row):
        if row["forecasted_units"] < 10:
            return "Heavy Discount"
        elif 10 <= row["forecasted_units"] < 18:
            if row["cv"] > 1.0:
                return "Moderate Discount"
            else:
                return "Light Discount"
        elif row["forecasted_units"] >= 18:
            if row["cv"] > 1.0:
                return "Scarcity Messaging"
            else:
                return "No Offer"
        else:
            return "No Offer"

    df["offer_applied"] = df.apply(label_offer, axis=1)

    # Step 4: Prepare output
    result = df[[
        "date", "product_id", "forecasted_units", "lower_bound", "upper_bound",
        "previous_day_units", "uncertainty", "cv", "offer_applied"
    ]]

    # Convert datetime to string
    result["date"] = result["date"].dt.strftime("%Y-%m-%d")

    # Replace NaN/inf with None for JSON compatibility
    result = result.replace({np.nan: None, np.inf: None, -np.inf: None})

    return result.to_dict(orient="records")