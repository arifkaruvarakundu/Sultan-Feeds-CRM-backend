from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class TopProduct(BaseModel):
    product_id: Optional[int]
    product_name: Optional[str]
    total_quantity: Optional[int]

# ✅ Add this model for all products summary
class ProductQuantitySummary(BaseModel):
    product_id: Optional[int]
    product_name: Optional[str]
    total_quantity: Optional[int]

class ProductOrderData(BaseModel):
    date: Optional[str]
    quantity: Optional[int]

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


class ProductItem(BaseModel):
    product_id: Optional[int]
    product_name: Optional[str]
    product_quantity: Optional[int]
    product_price: Optional[float]
    product_category: Optional[str]
    product_stock_status: Optional[str]
    product_weight: Optional[float]

class OrderDetail(BaseModel):
    order_id: Optional[int]
    external_order_id: Optional[int]
    order_status: Optional[str]
    order_total: Optional[float]
    order_date: Optional[datetime]
    payment_method: Optional[str]
    items: List[ProductItem]

class CustomerInfo(BaseModel):
    customer_id: Optional[int]
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

class ProductSummary(BaseModel):
    product_id: Optional[int]
    product_name: Optional[str]
    total_quantity: Optional[int]

class CustomerDetailsResponse(BaseModel):
    customer: CustomerInfo
    orders: List[OrderDetail]
    top_products: List[ProductSummary]
    all_products_summary: List[ProductSummary]