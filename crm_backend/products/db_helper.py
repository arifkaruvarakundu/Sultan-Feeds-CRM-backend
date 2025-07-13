from sqlalchemy import func
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
            func.sum(OrderItem.quantity).label("total_sales")
        )
        .join(OrderItem, Product.external_id == OrderItem.product_id)
        .join(Order, Order.id == OrderItem.order_id)
        .filter(Order.created_at >= start)
        .filter(Order.created_at <= end)
        .group_by(Product.id, Product.name, Product.categories)
        .order_by(func.sum(OrderItem.quantity).desc())
        .all()
    )

    return [
        {
            "id": p_id,
            "name": name,
            "category": categories,
            "total_sales": total_sales or 0
        }
        for p_id, name, categories, total_sales in results
    ]

def get_products_table_data(db: Session):

    products = db.query(Product).all()
    return [ProductSchema.from_orm(p) for p in products]
