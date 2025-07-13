from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ProductSchema(BaseModel):
    id: int
    external_id: Optional[int]
    name: str
    short_description: Optional[str]
    regular_price: Optional[float]
    sales_price: Optional[float]
    total_sales: Optional[int]
    categories: Optional[str]
    stock_status: Optional[str]
    weight: Optional[float]
    date_created: Optional[datetime]
    date_modified: Optional[datetime]
    
    model_config = {
        "from_attributes": True
    }
    
