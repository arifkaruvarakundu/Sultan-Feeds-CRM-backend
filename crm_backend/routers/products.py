from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from crm_backend.schemas.product import ProductSchema
from crm_backend.database import get_db
from crm_backend.models import *  # Assuming Customer model is imported
from crm_backend.products.operation_helper import *

router = APIRouter()


@router.get("/top-selling-products", response_model=List[dict])
def get_top_selling_products(db: Session = Depends(get_db)):

    response_data = function_get_top_selling_products(db=db)
    return response_data

@router.get("/top-products-inbetween", response_model=List[dict])
def get_top_selling_products_inbetween(db:Session = Depends(get_db), start_date: str = None, end_date: str = None):

    response_data = function_get_top_selling_products_inbetween(db=db, start_date=start_date, end_date=end_date)
    return response_data

@router.get("/products-sales-table", response_model=List[dict])
def get_products_sales_table(db:Session = Depends(get_db), start_date: str = None, end_date: str = None):

    response_data = function_get_products_sales_table(db=db, start_date=start_date, end_date= end_date)
    return response_data
    
@router.get("/products-table", response_model=List[ProductSchema])
def get_products_table(db:Session = Depends(get_db)):

    response_data = function_get_products_table(db)
    
    return response_data

@router.get("/product-details/{id}", response_model=List[ProductSchema])
def get_product_details(id: int, db: Session = Depends(get_db)):

    response_data = function_get_product_details(db, id)
    return response_data

@router.get("/product-sales-over-time", response_model=List[Dict[str, Any]])
def get_product_sales_over_time(start_date: str, end_date: str, product_id: int, db: Session = Depends(get_db)):

    response_data = function_get_sales_over_time(db=db, product_id=product_id, start_date=start_date, end_date= end_date)
    return response_data

@router.get("/segment-products", response_model = List[dict])
def get_segmented_product_data(db: Session = Depends(get_db)):

    response_data = function_get_segmented_product_data(db=db)
    return response_data