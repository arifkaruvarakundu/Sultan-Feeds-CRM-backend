from crm_backend.orders.db_helper import *

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

