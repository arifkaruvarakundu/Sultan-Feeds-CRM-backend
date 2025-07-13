from sqlalchemy.orm import Session
from crm_backend.models import *
from typing import List, Dict
from sqlalchemy import func, desc, text
from datetime import date, timedelta, datetime

def get_latest_orders_data(db: Session) -> List[dict]:
    orders = (
        db.query(Order)
        .order_by(Order.created_at.desc())
        .limit(5)
        .all()
    )

    return [
        {
            "id": f"#OD{order.id}",
            "user": order.customer.first_name if order.customer else "Unknown",
            "date": order.created_at.strftime("%d %b %Y"),
            "price": f"${order.total_amount:.2f}",
            "status": order.status,
        }
        for order in orders
    ]

def get_total_orders_count_data(db:Session) -> List[dict]:

    total_orders = db.query(Order).count()
    
    return [
        {
            "title": "Total Orders",
            "count": total_orders
        }
    ]


def get_total_sales_data(db: Session) -> List[dict]:
    total_sales = db.query(func.coalesce(func.sum(Order.total_amount), 0.0))\
                    .filter(Order.status == "completed")\
                    .scalar()

    return [
        {
            "titlesales": "Total Sales",
            "totalamount": round(total_sales, 2)  # Rounded to 2 decimal places
        }
    ]

def get_average_order_value_data(db: Session) -> List[dict]:
    total_sales = db.query(func.coalesce(func.sum(Order.total_amount), 0.0))\
                    .filter(Order.status == "completed")\
                    .scalar()

    completed_order_count = db.query(func.count(Order.id))\
                              .filter(Order.status == "completed")\
                              .scalar()

    # Avoid division by zero
    aov = total_sales / completed_order_count if completed_order_count > 0 else 0.0

    return [
        {
            "titleaov": "Average Order Value",
            "amount": round(aov, 2)
        }
    ]

def get_total_customers_count_data(db: Session) -> List[dict]:
    total_customers = db.query(func.count(Customer.id)).scalar()

    return [
        {
            "titlecustomers": "Total Customers",
            "countcustomers": total_customers
        }
    ]

def get_top_customers_data(db: Session, limit: int = 5) -> List[dict]:
    results = (
        db.query(
            Customer.first_name,
            Customer.last_name,
            func.count(Order.id).label("total_orders"),
            func.sum(Order.total_amount).label("total_spending")
        )
        .join(Order, Order.customer_id == Customer.id)
        .filter(Order.status == "completed")
        .group_by(Customer.id)
        .order_by(desc("total_spending"))
        .limit(limit)
        .all()
    )

    return [
        {
            "user": f"{row.first_name} {row.last_name}",
            "total_orders": row.total_orders,
            "total_spending": round(row.total_spending, 2)
        }
        for row in results
    ]

def get_sales_comparison_data(db: Session) -> dict:
    today = date.today()
    current_month = today.month
    current_year = today.year

    # Previous month calculation
    first_day_current = date(current_year, current_month, 1)
    last_day_prev = first_day_current - timedelta(days=1)
    prev_month = last_day_prev.month
    prev_year = last_day_prev.year

    # Sales this month up to today, excluding failed and cancelled
    current_month_query = text("""
        SELECT EXTRACT(DAY FROM created_at) AS day, SUM(total_amount) AS total
        FROM orders
        WHERE 
            EXTRACT(MONTH FROM created_at) = :month AND
            EXTRACT(YEAR FROM created_at) = :year AND
            created_at <= :today AND
            status NOT IN ('failed', 'cancelled')
        GROUP BY day
        ORDER BY day
    """)
    current_sales = db.execute(current_month_query, {
        "month": current_month,
        "year": current_year,
        "today": today
    }).fetchall()

    # Full previous month, excluding failed and cancelled
    prev_month_query = text("""
        SELECT EXTRACT(DAY FROM created_at) AS day, SUM(total_amount) AS total
        FROM orders
        WHERE 
            EXTRACT(MONTH FROM created_at) = :month AND
            EXTRACT(YEAR FROM created_at) = :year AND
            status NOT IN ('failed', 'cancelled')
        GROUP BY day
        ORDER BY day
    """)
    prev_sales = db.execute(prev_month_query, {
        "month": prev_month,
        "year": prev_year
    }).fetchall()

    return {
        "currentMonth": [{"day": int(row.day), "total": float(row.total)} for row in current_sales],
        "previousMonth": [{"day": int(row.day), "total": float(row.total)} for row in prev_sales]
    }






