import httpx
from sqlalchemy.orm import Session
from crm_backend.models import Customer, Address, Order, OrderItem, Product, SyncState
from crm_backend.tasks.send_whatsapp import send_whatsapp_template
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
from dateutil.parser import isoparse

load_dotenv()

WC_BASE_URL = "https://souqalsultan.com/wp-json/wc/v3/orders"
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

WHATSAPP_TEMPLATES = {
    "processing": "order_processing",
    "completed": "order_completed",
    "cancelled": "order_cancelled",
    "on-hold": "order_onhold",
    "failed": "order_failed"
    # Add more as needed
}

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

def get_last_synced_time(db: Session) -> str:
    state = db.query(SyncState).filter_by(key="last_order_sync").first()
    return state.value if state else "2000-01-01T00:00:00Z"

def set_last_synced_time(db: Session, timestamp: str) -> None:
    state = db.query(SyncState).filter_by(key="last_order_sync").first()
    if state:
        state.value = timestamp
    else:
        db.add(SyncState(key="last_order_sync", value=timestamp))
    db.commit()

def process_order_data(db: Session, data: dict) -> None:
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

    order_in_db = db.query(Order).filter_by(order_key=data["order_key"]).first()

    meta = data.get("meta_data", [])
    meta_dict = {entry.get("key"): entry.get("value") for entry in meta}

    if order_in_db:
        new_status = data["status"]
        updated = False

        if order_in_db.status != new_status:
            order_in_db.status = new_status
            updated = True

        new_payment_method = data.get("payment_method_title")
        if order_in_db.payment_method != new_payment_method:
            order_in_db.payment_method = new_payment_method
            updated = True

        if updated:
            db.add(order_in_db)
            db.flush()
            print(f"🔄 Updated order #{order_in_db.external_id} to status: {new_status}")

            if customer.phone:
                try:
                    full_name = f"{customer.first_name} {customer.last_name}".strip()
                    template_name = WHATSAPP_TEMPLATES.get(new_status)

                    if template_name:
                        send_whatsapp_template(
                            phone_number=customer.phone,
                            customer_name=full_name,
                            order_number=str(order_in_db.external_id),
                            template_name=template_name
                        )
                    else:
                        print(f"⚠️ No template configured for status: {new_status}")
                except Exception as e:
                    print(f"❌ WhatsApp send failed: {e}")

        return

    order = Order(
        order_key=data["order_key"],
        customer_id=customer.id,
        external_id=data["id"],
        status=data["status"],
        total_amount=float(data["total"]),
        created_at=isoparse(data["date_created"]),
        payment_method=data.get("payment_method_title"),
        attribution_referrer=meta_dict.get("_wc_order_attribution_referrer"),
        session_pages=int(meta_dict.get("_wc_order_attribution_session_pages", 0)),
        session_count=int(meta_dict.get("_wc_order_attribution_session_count", 0)),
        device_type=meta_dict.get("_wc_order_attribution_device_type")
    )
    db.add(order)
    db.flush()

    for item in data.get("line_items", []):
        product = db.query(Product).filter_by(external_id=item["product_id"]).first()
        product_id = product.external_id if product else None

        order_item = OrderItem(
            order_id=order.id,
            product_name=item["name"],
            product_id=product_id,
            quantity=item["quantity"],
            price=float(item["price"])
        )
        db.add(order_item)

    if customer.phone:
        try:
            full_name = f"{customer.first_name} {customer.last_name}".strip()
            template_name = WHATSAPP_TEMPLATES.get(order.status)

            if template_name:
                send_whatsapp_template(
                    phone_number=customer.phone,
                    customer_name=full_name,
                    order_number=str(order.external_id),
                    template_name=template_name
                )
            else:
                print(f"⚠️ No template configured for order status: {order.status}")
        except Exception as e:
            print(f"❌ WhatsApp send failed: {e}")

def fetch_and_save_orders(db: Session) -> None:
    print(f"[DB INFO] Connected to: {db.bind.url}")

    auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    per_page = 100
    page = 1

    four_days_ago = datetime.utcnow() - timedelta(days=4)
    after_date = four_days_ago.isoformat() + "Z"
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
                process_order_data(db, data)

            db.commit()
            print(f"✅ Committed page {page}")
        except Exception as e:
            db.rollback()
            print(f"❌ Error processing page {page}: {e}")

        page += 1

def fetch_all_orders_once(db: Session) -> None:
    print(f"[DB INFO] Starting full order fetch...")

    auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    per_page = 100
    page = 1

    while True:
        url = f"{WC_BASE_URL}?per_page={per_page}&page={page}"
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
            print("No more orders to fetch.")
            break

        print(f"Processing page {page}, {len(orders)} orders")

        try:
            for data in orders:
                process_order_data(db, data)

            db.commit()
            print(f"✅ Committed page {page}")
        except Exception as e:
            db.rollback()
            print(f"❌ Error processing page {page}: {e}")
            break

        page += 1

    latest_time = datetime.utcnow().isoformat() + "Z"
    set_last_synced_time(db, latest_time)

