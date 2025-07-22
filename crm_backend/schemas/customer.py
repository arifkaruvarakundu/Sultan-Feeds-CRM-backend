from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class CustomerDetail(BaseModel):
    customer_id: int
    first_name: Optional[str]
    last_name: Optional[str]
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    address_1: Optional[str]
    address_2: Optional[str]
    city: Optional[str]
    state: Optional[str]
    postcode: Optional[str]
    country: Optional[str]
    order_id: Optional[int]
    external_order_id: Optional[int]
    order_status: Optional[str]
    order_total: Optional[float]
    order_date: Optional[datetime]
    payment_method: Optional[str]
    product_id: Optional[int]
    product_name: Optional[str]
    product_quantity: Optional[int]
    product_price: Optional[float]
    product_category: Optional[str]
    product_stock_status: Optional[str]
    product_weight: Optional[float]

class TopProduct(BaseModel):
    product_id: Optional[int]
    product_name: Optional[str]
    total_quantity: Optional[int]

# ✅ Add this model for all products summary
class ProductQuantitySummary(BaseModel):
    product_id: Optional[int]
    product_name: Optional[str]
    total_quantity: Optional[int]

# ✅ Updated response model
class CustomerDetailsResponse(BaseModel):
    customer_details: List[CustomerDetail]
    top_products: List[TopProduct]
    all_products_summary: List[ProductQuantitySummary]

class ProductOrderData(BaseModel):
    date: str
    quantity: int

# class CustomerClassificationResponse(BaseModel):
#     customer_id: Optional[int]
#     customer_name: Optional[str]
#     order_count: Optional[int]
#     total_spent: Optional[float]
#     last_order_date: Optional[str]
#     classification: Optional[str]
#     spending_classification: Optional[str]

class CustomerClassificationResponse(BaseModel):
    customer_id: Optional[int]
    customer_name: Optional[str]
    phone: Optional[str]  
    order_count: Optional[int]
    total_spent: Optional[float]
    last_order_date: Optional[str]
    classification: Optional[str]
    spending_classification: Optional[str]
    churn_risk: Optional[str]
    segment: Optional[str]
