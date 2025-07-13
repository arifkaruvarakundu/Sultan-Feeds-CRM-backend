from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List

from crm_backend.database import get_db
from crm_backend.models import Order, Customer  # Assuming Customer model is imported
from crm_backend.orders.operation_helper import *

router = APIRouter()

@router.get("/latest-orders", response_model=List[dict])
def get_latest_orders(db: Session = Depends(get_db)):

    response_data = get_latest_orders_dashboard(db=db)
    return response_data

@router.get("/total-orders-count", response_model = List[dict])
def get_total_orders_count(db: Session = Depends(get_db)):

    response_data = function_get_total_orders_count(db=db)
    return response_data

@router.get("/total-sales", response_model = List[dict])
def get_total_sales(db: Session = Depends(get_db)):

    response_data = function_get_total_sales(db=db)
    return response_data

@router.get("/aov", response_model = List[dict])
def get_average_order_value(db: Session = Depends(get_db)):

    response_data = function_get_average_order_value(db=db)
    return response_data

@router.get("/total-customers", response_model = List[dict])
def get_total_customers_count(db: Session = Depends(get_db)):

    response_data = function_get_total_customers_count(db=db)
    return response_data

@router.get("/top-customers", response_model = List[dict])
def get_top_customers(db: Session = Depends(get_db)):

    response_data = function_get_top_customers(db)
    return response_data

@router.get("/sales-comparison")
def get_sales_comparison(db: Session = Depends(get_db)):

    response_data = function_get_sales_comparison(db)
    return response_data
