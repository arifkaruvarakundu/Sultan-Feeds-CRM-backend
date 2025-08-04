from sqlalchemy.orm import Session
from crm_backend.models import *
from typing import List, Dict
from sqlalchemy import func, desc, text, and_, case
from datetime import date, timedelta, datetime
from sqlalchemy.orm import Session, joinedload

def customers_table_data(db: Session) -> List[dict]:
    results = (
        db.query(
            Customer.id,
            Customer.first_name,
            Customer.last_name,
            Customer.phone,
            func.count(Order.id).label("total_orders"),
            func.sum(case((Order.status == "completed", Order.total_amount),else_=0)).label("total_spending")
        )
        .join(Order, Order.customer_id == Customer.id)
        # .filter(Order.status == "completed")
        .group_by(Customer.id)
        .order_by(desc("total_spending"))
        .all()
    )

    return [
        {
            "id": row.id,
            "user": f"{row.first_name} {row.last_name}",
            "phone": row.phone,
            "total_orders": row.total_orders,
            "total_spending": round(row.total_spending, 2)
        }
        for row in results
    ]

def get_customer_order_data_for_analysis(db: Session, id: int) -> dict:
    customer = db.query(Customer).options(
        joinedload(Customer.address),
        joinedload(Customer.orders).joinedload(Order.items).joinedload(OrderItem.product)
    ).filter(Customer.id == id).first()

    if not customer:
        return {}

    # Build customer base info (no repetition)
    customer_info = {
        "customer_id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "email": customer.email,
        "phone": customer.phone,
        "company": customer.address.company if customer.address else None,
        "address_1": customer.address.address_1 if customer.address else None,
        "address_2": customer.address.address_2 if customer.address else None,
        "city": customer.address.city if customer.address else None,
        "state": customer.address.state if customer.address else None,
        "postcode": customer.address.postcode if customer.address else None,
        "country": customer.address.country if customer.address else None
    }

    # Build orders with nested items
    orders_list = []
    all_records = []

    for order in customer.orders:
        items_list = []

        for item in order.items:
            product = item.product
            item_record = {
                "product_id": item.product_id,
                "product_name": item.product_name,
                "product_quantity": item.quantity,
                "product_price": item.price,
                "product_category": product.categories if product else None,
                "product_stock_status": product.stock_status if product else None,
                "product_weight": product.weight if product else None,
            }
            items_list.append(item_record)

            # Used for pandas aggregation
            all_records.append({
                **item_record,
                "order_status": order.status
            })

        orders_list.append({
            "order_id": order.id,
            "external_order_id": order.external_id,
            "order_status": order.status,
            "order_total": order.total_amount,
            "order_date": order.created_at,
            "payment_method": order.payment_method,
            "items": items_list
        })

    return {
        "customer": customer_info,
        "orders": orders_list,
        "raw_records": all_records  # Needed for analysis
    }

def get_customer_order_items_summary_data(db: Session, customer_id: int) -> List[Dict]:
    customer = db.query(Customer).options(
        joinedload(Customer.orders).joinedload(Order.items)
    ).filter(Customer.id == customer_id).first()

    if not customer or not customer.orders:
        return []

    records = []
    for order in customer.orders:
        for item in order.items:
            records.append({
                "order_id": order.id,
                "order_date": order.created_at,
                "product_name": item.product_name,
                "quantity": item.quantity
            })

    if not records:
        return []

    return records
    
def get_customer_product_orders_data(db: Session, customer_id: int, product_external_id: int):
    """
    Fetch order date and quantity for a specific product ordered by a specific customer.
    
    :param session: SQLAlchemy DB session
    :param customer_id: ID of the customer (internal DB ID)
    :param product_external_id: External ID of the product
    :return: List of {date, quantity}
    """
    results = (
        db.query(Order.created_at, OrderItem.quantity)
        .join(OrderItem, Order.id == OrderItem.order_id)
        .filter(
            and_(
                Order.customer_id == customer_id,
                OrderItem.product_id == product_external_id
            )
        )
        .order_by(Order.created_at)
        .all()
    )

    return [{"date": order.created_at.strftime("%Y-%m-%d"), "quantity": order.quantity} for order in results]

def get_customer_classification_data(db: Session):
    data = (
        db.query(
            Customer.id.label("customer_id"),
            func.concat(Customer.first_name, ' ', Customer.last_name).label("customer_name"),
            func.count(Order.id).label("order_count"),
            func.max(Order.created_at).label("last_order_date")  # Get latest order date
        )
        .outerjoin(Order, (Customer.id == Order.customer_id) & Order.status.in_(["completed", "processing"]))
        .group_by(Customer.id, Customer.first_name, Customer.last_name)
        .all()
    )

    return data

def get_spending_customer_classification_data(db: Session):
    data = (
        db.query(
            Customer.id.label("customer_id"),
            func.concat(Customer.first_name, ' ', Customer.last_name).label("customer_name"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
            func.max(Order.created_at).label("last_order_date")
        )
        .outerjoin(Order, (Customer.id == Order.customer_id) & Order.status.in_(["completed", "processing"]))
        .group_by(Customer.id, Customer.first_name, Customer.last_name)
        .all()
    )
    return data

def get_full_customer_classification_data(db: Session):
    """
    Fetches customer classification data including:
    - customer_id
    - customer_name
    - phone
    - order_count
    - total_spent
    - last_order_date

    Filters only 'completed' and 'processing' orders.
    """
    data = (
        db.query(
            Customer.id.label("customer_id"),
            func.concat(Customer.first_name, ' ', Customer.last_name).label("customer_name"),
            Customer.phone.label("phone"),
            func.count(Order.id).label("order_count"),
            func.coalesce(func.sum(Order.total_amount), 0).label("total_spent"),
            func.max(Order.created_at).label("last_order_date")
        )
        .outerjoin(Order, (Customer.id == Order.customer_id) & Order.status.in_(["completed", "processing"]))
        .group_by(Customer.id, Customer.first_name, Customer.last_name, Customer.phone)
        .all()
    )

    return data