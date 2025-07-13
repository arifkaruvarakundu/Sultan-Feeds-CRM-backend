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

