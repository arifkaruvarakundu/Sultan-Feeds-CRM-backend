from sqlalchemy import func, cast, Date
from sqlalchemy.orm import Session
from crm_backend.models import *
from typing import List, Dict
from fastapi import Query
from datetime import datetime
from crm_backend.schemas.product import ProductSchema

def get_top_selling_products_data(db: Session) -> List[dict]:
    results = (
        db.query(
            Product.name,
            func.sum(OrderItem.quantity).label("total_quantity_sold")
        )
        .join(OrderItem, Product.external_id == OrderItem.product_id)
        # .filter(Order.status == "completed")
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    # Return in format suitable for frontend
    return [
        {"name": name, "total_quantity_sold": quantity}
        for name, quantity in results
    ]

def get_top_selling_products_inbetween_data(db: Session, start_date: str, end_date: str):
    results = (
        db.query(
            Product.name,
            func.sum(OrderItem.quantity).label("total_quantity_sold")
        )
        .join(OrderItem, Product.external_id == OrderItem.product_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= start_date)
        .filter(Order.created_at <= end_date)
        .filter(Order.status == "completed")
        .group_by(Product.name)
        .order_by(func.sum(OrderItem.quantity).desc())
        .limit(5)
        .all()
    )

    return [
        {"name": name, "total_quantity_sold": quantity}
        for name, quantity in results
    ]

def get_products_sales_table_data(db: Session, start_date: str, end_date: str):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        return []

    results = (
        db.query(
            Product.id,
            Product.name,
            Product.categories,
            Product.sales_price,
            Product.regular_price,
            func.sum(OrderItem.quantity).label("total_sales")
        )
        .join(OrderItem, Product.external_id == OrderItem.product_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= start)
        .filter(Order.status == "completed")
        .filter(Order.created_at <= end)
        .group_by(
            Product.id,
            Product.name,
            Product.categories,
            Product.sales_price,
            Product.regular_price
        )
        .order_by(func.sum(OrderItem.quantity).desc())
        .all()
    )

    def clean_price(sp, rp):
        """Return sales_price if valid, else regular_price, else 0."""
    
        def to_float(val):
            try:
                if val is None:
                    return None
                if isinstance(val, str):
                    val = val.strip()
                    if val in ("", "0", "0.0"):
                        return None
                num = float(val)
                return num if num > 0 else None
            except (ValueError, TypeError):
                return None
        
        sp_val = to_float(sp)
        rp_val = to_float(rp)
        
        return sp_val if sp_val is not None else (rp_val if rp_val is not None else 0.0)

    return [
        {
            "id": p_id,
            "name": name,
            "category": categories,
            "price": clean_price(sales_price, regular_price),
            "total_sales": total_sales or 0
        }
        for p_id, name, categories, sales_price, regular_price, total_sales in results
    ]

def get_products_table_data(db: Session):

    products = db.query(Product).all()
    return [ProductSchema.from_orm(p) for p in products]

def get_product_details_data(db: Session, id: int) -> dict:
    
    return db.query(Product).filter(Product.id == id).all() 

def get_sales_over_time_data(db: Session, start_date: str, end_date: str, product_id: int):
    try:
        start = datetime.fromisoformat(start_date)
        end = datetime.fromisoformat(end_date)
    except ValueError:
        return []

    results = (
        db.query(
            Product.name.label("product_name"),
            Product.external_id.label("external_id"),
            cast(Order.created_at, Date).label("date"),
            func.sum(OrderItem.quantity).label("total_sales")
        )
        .join(OrderItem, Product.external_id == OrderItem.product_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= start)
        .filter(Order.created_at <= end)
        .filter(Order.status == "completed")
        .filter(Product.id == product_id)
        .group_by(Product.name, Product.external_id, cast(Order.created_at, Date))
        .order_by(cast(Order.created_at, Date))
        .all()
    )

    # Combine rows under one product object for frontend charting
    return [
        {
            "product": row.product_name,
            "date": row.date.isoformat(),
            "external_id": row.external_id,
            "total_sales": row.total_sales
        }
        for row in results
    ]