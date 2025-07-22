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

