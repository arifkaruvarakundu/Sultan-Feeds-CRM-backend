import httpx
from sqlalchemy.orm import Session
from crm_backend.models import Customer, Address, Order, OrderItem, Product, SyncState
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

def update_orders_from_api(db: Session, api_data: list):
    for order_data in api_data:
        order_key = order_data.get("order_key")
        status = order_data.get("status")
        meta = {meta["key"]: meta["value"] for meta in order_data.get("meta_data", [])}

        # Extract values from meta
        attribution_referrer = meta.get("_wc_order_attribution_referrer")
        session_pages = meta.get("_wc_order_attribution_session_pages")
        session_count = meta.get("_wc_order_attribution_session_count")
        device_type = meta.get("_wc_order_attribution_device_type")

        # Convert types if needed (some may come as strings)
        try:
            session_pages = int(session_pages) if session_pages is not None else None
        except ValueError:
            session_pages = None

        try:
            session_count = int(session_count) if session_count is not None else None
        except ValueError:
            session_count = None

        # Find order in DB
        order = db.query(Order).filter(Order.order_key == order_key).first()
        if not order:
            continue  # Skip if order not found

        # Update order fields
        order.status = status
        order.attribution_referrer = attribution_referrer
        order.session_pages = session_pages
        order.session_count = session_count
        order.device_type = device_type

    db.commit()

def backfill_existing_orders(db: Session):
    orders = db.query(Order).all()

    for order in orders:
        print(f"Backfilling order: {order.external_id}")
        # Fetch from API
        url = f"{WC_BASE_URL}/{order.external_id}"
        try:
            with httpx.Client() as client:
                response = client.get(url, auth=(WC_CONSUMER_KEY, WC_CONSUMER_SECRET))
            if response.status_code != 200:
                print(f"Failed to fetch order {order.external_id}: {response.text}")
                continue

            data = response.json()
            meta = {m["key"]: m["value"] for m in data.get("meta_data", [])}

            order.attribution_referrer = meta.get("_wc_order_attribution_referrer")
            order.session_pages = int(meta.get("_wc_order_attribution_session_pages", 0))
            order.session_count = int(meta.get("_wc_order_attribution_session_count", 0))
            order.device_type = meta.get("_wc_order_attribution_device_type")

        except Exception as e:
            print(f"Error updating order {order.external_id}: {e}")
            continue

    db.commit()
    print("✅ Finished backfilling existing orders.")

def fetch_and_save_orders(db: Session) -> None:
    """Fetch new WooCommerce orders since last sync and save to the database."""
    print(f"[DB INFO] Connected to: {db.bind.url}")

    auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    per_page = 100
    page = 1
    latest_order = db.query(Order).order_by(Order.created_at.desc()).first()
    after_date = latest_order.created_at.isoformat() if latest_order else "2000-01-01T00:00:00Z"
    # after_date = get_last_synced_time(db)
    # after_date = get_last_synced_time(db)
    # first_sync = after_date == "2000-01-01T00:00:00Z"
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

                order_in_db = db.query(Order).filter_by(order_key=data["order_key"]).first()
                if order_in_db:
                    # Update existing order with new metadata
                    update_orders_from_api(db, [data])
                    continue  # Don't re-insert

                meta = data.get("meta_data", [])
                meta_dict = {entry.get("key"): entry.get("value") for entry in meta}

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
            
            # # ✅ Update sync timestamp
            if first_sync and orders:
                last_order_created = max(isoparse(order["date_created"]) for order in orders)
                set_last_synced_time(db, last_order_created.isoformat())

        except Exception as e:
            db.rollback()
            print(f"❌ Failed to save orders from page {page}: {e}")
        page += 1
