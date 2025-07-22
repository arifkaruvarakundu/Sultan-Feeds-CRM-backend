from crm_backend.customers.db_helper import *
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
import numpy as np

def function_get_customers_table(db):
    customers_data = customers_table_data(db)

    return customers_data

def function_get_customers_details(db, id: int):
    customers_details = get_customer_order_data_for_analysis(db, id)

    # Load into pandas DataFrame
    df = pd.DataFrame(customers_details)

    # ✅ Filter only completed orders
    df_completed = df[df["order_status"] == "completed"]

    # Group by product and sum quantity
    top_products = (
        df_completed.groupby(["product_id", "product_name"], as_index=False)
        .agg(total_quantity=("product_quantity", "sum"))
        .sort_values(by="total_quantity", ascending=False)
        .head(5)
    )

    # Convert to list of dicts
    top_products_list = top_products.to_dict(orient="records")

    # ✅ Group all products (not limited to top 5) and sum quantities
    all_products = (
        df_completed.groupby(["product_id", "product_name"], as_index=False)
        .agg(total_quantity=("product_quantity", "sum"))
        .sort_values(by="product_name")
    )
    all_products_list = all_products.to_dict(orient="records")

    return {
        "customer_details": customers_details,
        "top_products": top_products_list,
        "all_products_summary": all_products_list
    }

def function_get_customer_order_items_summary(db, id: int):
    order_items_summary = get_customer_order_items_summary_data(db, id)

    if not order_items_summary:
        return []

    df = pd.DataFrame(order_items_summary)

    if "order_date" not in df.columns:
        raise ValueError("Missing 'order_date' in data.")

    # Convert to datetime
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    # Extract only the date part for grouping
    df["order_date_only"] = df["order_date"].dt.date

    # Group and sort
    grouped = (
        df.groupby(["order_date_only", "product_name"], as_index=False)
        .agg(total_quantity=("quantity", "sum"))
        .sort_values(by=["order_date_only", "product_name"])
    )

    return grouped.to_dict(orient="records")

def function_get_customer_product_orders(db, customer_id: int, product_external_id: int):
    customer_product_orders = get_customer_product_orders_data(db, customer_id, product_external_id)
    return customer_product_orders

# def function_get_customer_classification(db):
#     customer_classification_data = get_customer_classification_data(db)

#     df = pd.DataFrame(customer_classification_data, columns=[
#         "customer_id", "customer_name", "order_count", "last_order_date"
#     ])

#     # Step 1: Ensure correct types
#     df["order_count"] = df["order_count"].fillna(0).astype(int)
#     df["last_order_date"] = pd.to_datetime(df["last_order_date"], errors='coerce')

#     # Step 2: Define classification logic
#     def classify(row):
#         count = row["order_count"]
#         last_date = row["last_order_date"]

#         cutoff_date = datetime(2025, 1, 1)
#         if count == 1 and pd.notnull(last_date) and last_date < cutoff_date:
#             return "Dead"
#         elif count == 1:
#             return "New"
#         elif 2 <= count <= 5:
#             return "Occasional"
#         elif 6 <= count <= 15:
#             return "Frequent"
#         elif count >= 16:
#             return "Loyal"
#         else:
#             return "No Orders"

#     df["classification"] = df.apply(classify, axis=1)

#     # Format datetime to ISO string
#     df["last_order_date"] = df["last_order_date"].apply(
#         lambda x: x.isoformat() if pd.notnull(x) else None
#     )

#     # Convert to clean native Python dicts
#     clean_records = [
#         {
#             "customer_id": int(row["customer_id"]),
#             "customer_name": str(row["customer_name"]),
#             "order_count": int(row["order_count"]),
#             "last_order_date": row["last_order_date"],
#             "classification": str(row["classification"]),
#             "spending_classification": None,
#             "total_spent": None
#         }
#         for _, row in df.iterrows()
#     ]

#     return clean_records

# def function_get_customer_classification(db):
#     customer_classification_data = get_customer_classification_data(db)

#     df = pd.DataFrame(customer_classification_data, columns=[
#         "customer_id", "customer_name", "order_count", "last_order_date"
#     ])

#     df["order_count"] = df["order_count"].fillna(0).astype(int)
#     df["last_order_date"] = pd.to_datetime(df["last_order_date"], errors='coerce')

#     # ------------------------
#     # Classification (existing logic)
#     # ------------------------
#     def classify(row):
#         count = row["order_count"]
#         last_date = row["last_order_date"]
#         cutoff_date = datetime(2025, 1, 1)

#         if count == 1 and pd.notnull(last_date) and last_date < cutoff_date:
#             return "Dead"
#         elif count == 1:
#             return "New"
#         elif 2 <= count <= 5:
#             return "Occasional"
#         elif 6 <= count <= 15:
#             return "Frequent"
#         elif count >= 16:
#             return "Loyal"
#         else:
#             return "No Orders"

#     df["classification"] = df.apply(classify, axis=1)

#     # ------------------------
#     # Churn risk
#     # ------------------------
#     today = datetime.now()
#     def churn_risk(date):
#         if pd.isnull(date):
#             return "High"
#         days_since = (today - date).days
#         if days_since < 30:
#             return "Low"
#         elif days_since < 90:
#             return "Medium"
#         else:
#             return "High"

#     df["churn_risk"] = df["last_order_date"].apply(churn_risk)

#     # ------------------------
#     # ML Segmentation using KMeans
#     # ------------------------
#     df["recency_days"] = df["last_order_date"].apply(
#         lambda d: (today - d).days if pd.notnull(d) else 999
#     )

#     # Filter customers with at least one order
#     df_for_clustering = df[df["order_count"] > 0][["order_count", "recency_days"]]

#     # Normalize
#     scaler = StandardScaler()
#     X_scaled = scaler.fit_transform(df_for_clustering)

#     # KMeans
#     kmeans = KMeans(n_clusters=4, random_state=42, n_init="auto")
#     df.loc[df["order_count"] > 0, "segment"] = kmeans.fit_predict(X_scaled).astype(int)

#     # Customers with no orders → "Unsegmented"
#     df["segment"] = df["segment"].fillna("Unsegmented")

#     # Optional: label segments (custom mapping or descriptive)
#     segment_map = {
#         0: "Loyal At-Risk",       # Previously: At-Risk Customers — High orders, but declining
#         1: "Dormant Customers",   # Previously: Churned — Moderate orders, long time ago
#         2: "Cold Leads",          # Previously: Engaged — Low order count, very stale
#         3: "Lost One-Timers",     # Previously: Power Buyers — 1–2 orders, 3+ years ago
#     }

#     df["segment"] = df["segment"].apply(lambda x: segment_map.get(x, x))

#     # ------------------------
#     # Final output
#     # ------------------------
#     df["last_order_date"] = df["last_order_date"].apply(
#         lambda x: x.isoformat() if pd.notnull(x) else None
#     )

#     print(df.groupby("segment")[["order_count", "recency_days"]].mean())

#     return [
#         {
#             "customer_id": int(row["customer_id"]),
#             "customer_name": str(row["customer_name"]),
#             "order_count": int(row["order_count"]),
#             "last_order_date": row["last_order_date"],
#             "classification": row["classification"],
#             "churn_risk": row["churn_risk"],
#             "segment": row["segment"],
#             "total_spent": None,
#             "spending_classification": None
#         }
#         for _, row in df.iterrows()
#     ]

# def function_get_spending_customer_classification_data(db):
#     customer_classification_data = get_spending_customer_classification_data(db)

#     df = pd.DataFrame(customer_classification_data, columns=[
#         "customer_id", "customer_name", "order_count", "total_spent", "last_order_date"
#     ])

#     df["order_count"] = df["order_count"].fillna(0).astype(int)
#     df["total_spent"] = df["total_spent"].fillna(0).astype(float)
#     df["last_order_date"] = pd.to_datetime(df["last_order_date"], errors='coerce')

#     def classify_spending(amount):
#         if amount < 50:
#             return "Low Spender"
#         elif 50 <= amount < 200:
#             return "Medium Spender"
#         elif 200 <= amount < 1000:
#             return "High Spender"
#         else:
#             return "VIP"

#     df["spending_classification"] = df["total_spent"].apply(classify_spending)

#     df["last_order_date"] = df["last_order_date"].apply(
#         lambda x: x.isoformat() if pd.notnull(x) else None
#     )

#     return [
#         {
#             "customer_id": int(row["customer_id"]),
#             "customer_name": str(row["customer_name"]),
#             "order_count": int(row["order_count"]),
#             "total_spent": float(row["total_spent"]),
#             "last_order_date": row["last_order_date"],
#             "spending_classification": row["spending_classification"],
#             "classification": None,
#             "churn_risk": None,
#             "segment":None
#         }
#         for _, row in df.iterrows()
#     ]

# --------------------------
# Helper Functions
# --------------------------

def classify_behavior(order_count, last_order_date, cutoff_date=datetime(2025, 1, 1)):
    """
    Classify customers based on their order count and last order date.

    Args:
        order_count (int): Number of orders placed by the customer.
        last_order_date (datetime or None): Date of the last order.
        cutoff_date (datetime): Reference date to distinguish old vs new customers.

    Returns:
        str: One of 'New', 'Dead', 'Occasional', 'Frequent', 'Loyal', or 'No Orders'.
    """
    if order_count == 1 and pd.notnull(last_order_date) and last_order_date < cutoff_date:
        return "Dead"
    elif order_count == 1:
        return "New"
    elif 2 <= order_count <= 5:
        return "Occasional"
    elif 6 <= order_count <= 15:
        return "Frequent"
    elif order_count >= 16:
        return "Loyal"
    else:
        return "No Orders"

def calculate_churn_risk(last_order_date, today=None):
    """
    Determine churn risk based on how long ago the last order was placed.

    Args:
        last_order_date (datetime or None): Date of last order.
        today (datetime, optional): Reference date; defaults to now.

    Returns:
        str: 'Low', 'Medium', or 'High' risk.
    """
    today = today or datetime.now()
    if pd.isnull(last_order_date):
        return "High"
    days_since = (today - last_order_date).days
    if days_since < 30:
        return "Low"
    elif days_since < 90:
        return "Medium"
    else:
        return "High"


def classify_spending(total_spent):
    """
    Classify customers based on total spending.

    Args:
        total_spent (float): Total monetary value spent by the customer.

    Returns:
        str: One of 'Low Spender', 'Medium Spender', 'High Spender', or 'VIP'.
    """
    if total_spent < 50:
        return "Low Spender"
    elif 50 <= total_spent < 200:
        return "Medium Spender"
    elif 200 <= total_spent < 1000:
        return "High Spender"
    else:
        return "VIP"

def segment_customers_kmeans(df, today):
    """
    Apply KMeans clustering based on order count and recency.

    Args:
        df (DataFrame): DataFrame with 'order_count' and 'last_order_date'.
        today (datetime): Reference date to calculate recency.

    Returns:
        DataFrame: Modified DataFrame with a 'segment' column.
    """
    df["recency_days"] = df["last_order_date"].apply(
        lambda d: (today - d).days if pd.notnull(d) else 999
    )
    clustering_df = df[df["order_count"] > 0][["order_count", "recency_days"]]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(clustering_df)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init="auto")
    df.loc[df["order_count"] > 0, "segment"] = kmeans.fit_predict(X_scaled).astype(int)

    segment_map = {
        0: "Loyal At-Risk",
        1: "Dormant Customers",
        2: "Cold Leads",
        3: "Lost One-Timers"
    }
    df["segment"] = df["segment"].apply(lambda x: segment_map.get(x, "Unsegmented"))
    return df

# --------------------------
# Main Function
# --------------------------

def function_get_full_customer_classification(db):
    # Fetch data
    customer_data = get_full_customer_classification_data(db)
    
    # SAFELY convert query result to DataFrame using column labels
    df = pd.DataFrame([dict(row._mapping) for row in customer_data])
    
    # Clean data
    df["order_count"] = df["order_count"].fillna(0).astype(int)
    df["total_spent"] = df["total_spent"].fillna(0).astype(float)
    df["last_order_date"] = pd.to_datetime(df["last_order_date"], errors='coerce')

    today = datetime.now()

    # Apply classifications
    df["classification"] = df.apply(
        lambda row: classify_behavior(row["order_count"], row["last_order_date"]), axis=1
    )
    df["churn_risk"] = df["last_order_date"].apply(lambda x: calculate_churn_risk(x, today))
    df["spending_classification"] = df["total_spent"].apply(classify_spending)

    # Apply segmentation
    df = segment_customers_kmeans(df, today)

    # Format date
    df["last_order_date"] = df["last_order_date"].apply(
        lambda x: x.isoformat() if pd.notnull(x) else None
    )

    # Optional inspection
    print(df.groupby("segment")[["order_count", "recency_days", "total_spent"]].mean())

    # Final return structure
    return [
        {
            "customer_id": int(row["customer_id"]),
            "customer_name": str(row["customer_name"]),
            "phone": row["phone"],
            "order_count": int(row["order_count"]),
            "total_spent": float(row["total_spent"]),
            "last_order_date": row["last_order_date"],
            "classification": row["classification"],
            "churn_risk": row["churn_risk"],
            "segment": row["segment"],
            "spending_classification": row["spending_classification"]
        }
        for _, row in df.iterrows()
    ]
