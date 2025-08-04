from crm_backend.orders.db_helper import *
import pandas as pd
from urllib.parse import urlparse

def get_latest_orders_dashboard(db):

    latest_orders_response = get_latest_orders_data(db)

    return latest_orders_response

def function_get_total_orders_count(db):

    total_orders_count = get_total_orders_count_data(db) 

    return total_orders_count

def function_get_total_sales(db):

    total_sales = get_total_sales_data(db)
    return total_sales

def function_get_average_order_value(db):

    aov_data = get_average_order_value_data(db)
    return aov_data

def function_get_total_customers_count(db):

    total_customers_data = get_total_customers_count_data(db)
    return total_customers_data

def function_get_top_customers(db):

    top_customers_data = get_top_customers_data(db)
    return top_customers_data

def function_get_sales_comparison(db):

    sales_comparison_data = get_sales_comparison_data(db)
    return sales_comparison_data

def function_get_orders_in_range(start_date, end_date, db, granularity="daily"):
    
    orders_in_range = get_orders_in_range_data(db, start_date, end_date, granularity)
    return orders_in_range

def function_get_orders_data(db):
    orders_data = get_orders_data(db)
    return orders_data

# Mapping of domains to labels
REFERRER_MAPPINGS = {
    'google.com': 'google',
    'instagram.com': 'instagram',
    'l.instagram.com': 'instagram',
    'souqalsultan.com': 'souqalsultan',
    'linktr.ee': 'linktree',
    'kpay.com.kw': 'knet',
    'facebook.com': 'facebook',
    'l.facebook.com': 'facebook',
    'fbclid=': 'facebook',
}

def map_referrer(ref: str) -> str:
    if not ref or ref.lower() == "unknown":
        return "Unknown"

    # Check query param pattern
    if 'fbclid=' in ref:
        return 'facebook'

    domain = urlparse(ref).netloc.lower()

    for key, label in REFERRER_MAPPINGS.items():
        if key in domain:
            return label

    return domain or "Unknown"

def function_get_attribution_summary(db: Session) -> List[dict]:
    results = get_attribution_summary(db)

    if not results:
        return []

    df = pd.DataFrame(results)
    df["mapped_referrer"] = df["referrer"].apply(map_referrer)

    summary_df = df.groupby("mapped_referrer", as_index=False)["count"].sum()
    return summary_df.to_dict(orient="records")

def function_get_orders_by_location(db: Session) -> List[dict]:
    # Get city-level order data from Kuwait
    results = get_orders_by_location_data(db)

    if not results:
        return []

    # Load into DataFrame
    df = pd.DataFrame(results)

    # Ensure required columns exist
    df["city"] = df["city"].fillna("Unknown")
    df["orders"] = df["orders"].fillna(0)

    # Group by city and sum orders (though it's already grouped)
    grouped_df = df.groupby(["city"], as_index=False)["orders"].sum()

    # Add coordinates if needed (merge back with first df if needed)
    if "coordinates" in df.columns:
        # Keep only one coordinate per city (first)
        coord_map = df.drop_duplicates("city")[["city", "coordinates"]]
        grouped_df = grouped_df.merge(coord_map, on="city", how="left")

    return grouped_df.to_dict(orient="records")

def function_get_orders_orderid_city(db: Session) -> list[dict]:
    """
    Get unique order count per city and process with pandas.
    
    Args:
        db (Session): SQLAlchemy database session.
    
    Returns:
        list[dict]: List of dicts with city and order_count.
    """
    results = get_unique_order_count_per_city(db)  # already has city + unique_order_count
    
    df = pd.DataFrame(results)[["city", "unique_order_count"]]
    df = df.rename(columns={"unique_order_count": "order_count"})  # rename for clarity
    
    return df.to_dict(orient="records")