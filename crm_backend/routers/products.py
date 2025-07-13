from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
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

# @router.get("/products", response_model=List[ProductSchema])
# def read_products(db: Session = Depends(get_db)):
#     products = db.query(Product).all()
#     return [ProductSchema.from_orm(p) for p in products]
