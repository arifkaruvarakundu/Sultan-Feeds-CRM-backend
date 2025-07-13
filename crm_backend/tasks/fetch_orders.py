import httpx
from sqlalchemy.orm import Session
from crm_backend.models import Customer, Address, Order, OrderItem, Product
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
from dateutil.parser import isoparse

load_dotenv()

WC_BASE_URL = "https://souqalsultan.com/wp-json/wc/v3/orders"
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

def normalize_phone(phone: str | None) -> str | None:
    """Remove spaces and country code prefix for consistency."""
    if phone:
        phone = phone.strip().replace(" ", "")
        if phone.startswith("+965"):
            phone = phone[4:]
        elif phone.startswith("00965"):
            phone = phone[5:]
        if not phone:
            return None
        return phone
    return None

def normalize_existing_phones(db: Session) -> None:
    customers = db.query(Customer).all()
    updated = False
    for customer in customers:
        original_phone = customer.phone
        normalized_phone = normalize_phone(original_phone)

        if normalized_phone != original_phone:
            # Check if another customer already has this normalized phone
            existing = (
                db.query(Customer)
                .filter(Customer.phone == normalized_phone)
                .filter(Customer.id != customer.id)
                .first()
            )
            if existing:
                print(f"Skipping Customer ID {customer.id}: {original_phone} -> {normalized_phone} (conflict with Customer ID {existing.id})")
                continue  # skip update

            print(f"Updating Customer ID {customer.id}: {original_phone} -> {normalized_phone}")
            customer.phone = normalized_phone
            updated = True

    if updated:
        db.commit()

def fetch_and_save_orders(db: Session) -> None:
    """Fetch new WooCommerce orders since last sync and save to the database."""
    print(f"[DB INFO] Connected to: {db.bind.url}")

    auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    per_page = 100
    page = 1
    latest_order = db.query(Order).order_by(Order.created_at.desc()).first()
    after_date = latest_order.created_at.isoformat() if latest_order else "2000-01-01T00:00:00Z"
    # after_date = "2025-07-07T11:55:13"
    print(f"Fetching orders created after {after_date}")

    while True:
        url = f"{WC_BASE_URL}?per_page={per_page}&page={page}&after={after_date}"
        try:
            with httpx.Client() as client:
                response = client.get(url, auth=auth)
        except Exception as e:
            print(f"Exception while fetching orders: {e}")
            break

        if response.status_code != 200:
            print(f"Error fetching orders: {response.text}")
            break

        orders = response.json()
        if not orders:
            break

        print(f"Processing page {page}, {len(orders)} new orders")
        try:
            for data in orders:
                email = data["billing"].get("email") or None
                raw_phone = data["billing"].get("phone") or None
                phone = normalize_phone(raw_phone)

                customer = None
                if phone:
                    customer = db.query(Customer).filter_by(phone=phone).first()
                if not customer and email:
                    customer = db.query(Customer).filter_by(email=email).first()

                if not customer:
                    customer = Customer(
                        first_name=data["billing"].get("first_name", ""),
                        last_name=data["billing"].get("last_name", ""),
                        email=email,
                        phone=phone,
                    )
                    db.add(customer)
                    db.flush()

                existing_address = db.query(Address).filter_by(
                    customer_id=customer.id,
                    address_1=data["billing"].get("address_1", ""),
                    city=data["billing"].get("city", ""),
                    postcode=data["billing"].get("postcode", "")
                ).first()

                if not existing_address:
                    address = Address(
                        customer_id=customer.id,
                        company=data["billing"].get("company"),
                        address_1=data["billing"].get("address_1"),
                        address_2=data["billing"].get("address_2"),
                        city=data["billing"].get("city"),
                        state=data["billing"].get("state"),
                        postcode=data["billing"].get("postcode"),
                        country=data["billing"].get("country")
                    )
                    db.add(address)

                if db.query(Order).filter_by(order_key=data["order_key"]).first():
                    continue  # Skip if order exists

                order = Order(
                    order_key=data["order_key"],
                    customer_id=customer.id,
                    external_id=data["id"],
                    status=data["status"],
                    total_amount=float(data["total"]),
                    created_at=isoparse(data["date_created"]),
                    payment_method=data.get("payment_method_title")
                )
                db.add(order)
                db.flush()

                for item in data.get("line_items", []):
                    product = db.query(Product).filter_by(external_id=item["product_id"]).first()
                    product_id = product.external_id if product else None  # ✅ foreign-key-safe

                    order_item = OrderItem(
                        order_id=order.id,
                        product_name=item["name"],
                        product_id=product_id,  # ✅ correct value
                        quantity=item["quantity"],
                        price=float(item["price"])
)
                    db.add(order_item)
            db.commit()
            print(f"Committed page {page}")
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to save orders from page {page}: {e}")
        page += 1
