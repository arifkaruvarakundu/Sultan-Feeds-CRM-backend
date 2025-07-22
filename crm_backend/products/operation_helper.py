from crm_backend.products.db_helper import *

def function_get_top_selling_products(db):

    top_selling_products_response = get_top_selling_products_data(db)

    return top_selling_products_response

def function_get_top_selling_products_inbetween(db, start_date, end_date):

    top_selling_products_inbetween_response = get_top_selling_products_inbetween_data(db,start_date, end_date)

    return top_selling_products_inbetween_response

def function_get_products_sales_table(db, start_date, end_date):

    products_sales_table_response = get_products_sales_table_data(db, start_date, end_date)
    
    return products_sales_table_response

def function_get_products_table(db):

    products_table_response = get_products_table_data(db)

    return products_table_response

def function_get_product_details(db, id: int):

    sales_comparison_data = get_product_details_data(db, id)
    return sales_comparison_data

def function_get_sales_over_time(db, start_date, end_date, product_id):

    sales_over_time_data = get_sales_over_time_data(db, start_date, end_date, product_id)

    return sales_over_time_data

#helper function

def segment_products(data):
    """
    Apply KMeans clustering to segment products based on key metrics.
    """
    df = pd.DataFrame(data, columns=[
        "product_id", "product_name", "regular_price", "sales_price", "stock_status",
        "total_units_sold", "total_revenue", "last_sold_date"
    ])

    # Fill and compute fields
    df["regular_price"] = df["regular_price"].fillna(0)
    df["sales_price"] = df["sales_price"].fillna(df["regular_price"])
    df["last_sold_date"] = pd.to_datetime(df["last_sold_date"], errors='coerce')

    today = datetime.now()
    df["recency_days"] = df["last_sold_date"].apply(lambda d: (today - d).days if pd.notnull(d) else 999)
    df["avg_price"] = df["total_revenue"] / df["total_units_sold"].replace(0, 1)

    # Features to cluster on
    features = df[["total_units_sold", "total_revenue", "avg_price", "recency_days"]]

    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(features)

    kmeans = KMeans(n_clusters=4, random_state=42, n_init="auto")
    df["segment"] = kmeans.fit_predict(X_scaled)

    # Map segments (example, based on patterns you observe)
    segment_map = {
        0: "Low Performer",
        1: "Best Seller",
        2: "Hidden Gem",
        3: "Recent Spike"
    }
    df["segment"] = df["segment"].apply(lambda x: segment_map.get(x, f"Segment {x}"))

    return df[[
        "product_id", "product_name", "total_units_sold", "total_revenue",
        "avg_price", "recency_days", "stock_status", "segment"
    ]]

def function_get_segmented_product_data(db: Session):

    raw_data = get_product_segmentation_data(db)
    df = segment_products(raw_data)
    return df.to_dict(orient="records")

