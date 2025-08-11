from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
import pandas as pd
from dotenv import load_dotenv
import os
from prophet import Prophet
import matplotlib.pyplot as plt  # Needed for plotting
from crm_backend.models import *  # Ensure your models are defined

# Load environment variables
load_dotenv()

# Setup SQLAlchemy engine and session
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
        .filter(Order.created_at >= '2025-01-01')  # You can change this date as needed
    )

    df = pd.read_sql(query.statement, session.bind)
    return df

def fetch_customer_order_data(customer_id: int):
    query = (
        session.query(
            Customer.id.label("customer_id"),
            OrderItem.product_id.label("product_id"),
            OrderItem.product_name.label("product_name"),
            Order.created_at.label("order_date"),
            OrderItem.quantity.label("quantity"),
        )
        .join(Order, Customer.id == Order.customer_id)
        .join(OrderItem, Order.id == OrderItem.order_id)
        # .filter(Order.created_at >= '2025-01-01')
        .filter(Customer.id == customer_id)
    )

    df = pd.read_sql(query.statement, session.bind)
    return df