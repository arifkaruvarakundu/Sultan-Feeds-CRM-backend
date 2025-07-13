import httpx
from sqlalchemy.orm import Session
from crm_backend.models import Product
from datetime import datetime, timezone
import os
from dotenv import load_dotenv
# from dateutil.parser import isoparse

load_dotenv()

WC_BASE_URL = "https://souqalsultan.com/wp-json/wc/v3/products"
WC_CONSUMER_KEY = os.getenv("WC_CONSUMER_KEY")
WC_CONSUMER_SECRET = os.getenv("WC_CONSUMER_SECRET")

def fetch_and_save_products(db: Session) -> None:
    """Fetch products from WooCommerce and save to the database."""
    auth = (WC_CONSUMER_KEY, WC_CONSUMER_SECRET)
    per_page = 100
    page = 1

    print(f"[DB INFO] Connected to: {db.bind.url}")

    while True:
        url = f"{WC_BASE_URL}/?per_page={per_page}&page={page}"
        print(f"Fetching page {page} of products...")

        try:
            with httpx.Client() as client:
                response = client.get(url, auth=auth)
        except Exception as e:
            print(f"❌ HTTP exception while fetching products: {e}")
            break

        if response.status_code != 200:
            print(f"❌ Failed to fetch products: {response.text}")
            break

        products = response.json()
        if not products:
            print("✅ No more products to process.")
            break

        try:
            for data in products:
                existing = db.query(Product).filter_by(external_id=data["id"]).first()

                date_created = data.get("date_created")
                date_modified = data.get("date_modified")

                if date_created:
                    date_created = datetime.fromisoformat(date_created.replace("Z", "+00:00"))
                if date_modified:
                    date_modified = datetime.fromisoformat(date_modified.replace("Z", "+00:00"))

                if existing:
                    # Update existing product if needed
                    existing.name = data["name"]
                    existing.short_description = data.get("short_description")
                    existing.regular_price = float(data.get("regular_price") or 0)
                    existing.sales_price = float(data.get("sale_price") or 0)
                    existing.total_sales = data.get("total_sales") or 0
                    existing.categories = ", ".join([cat["name"] for cat in data.get("categories", [])])
                    existing.stock_status = data.get("stock_status")
                    existing.weight = float(data.get("weight") or 0)
                    if date_created:
                        existing.date_created = date_created
                    if date_modified:
                        existing.date_modified = date_modified 
                else:
                    product = Product(
                        external_id=data["id"],
                        name=data["name"],
                        short_description=data.get("short_description"),
                        regular_price=float(data.get("regular_price") or 0),
                        sales_price=float(data.get("sale_price") or 0),
                        total_sales=data.get("total_sales") or 0,
                        categories=", ".join([cat["name"] for cat in data.get("categories", [])]),
                        stock_status=data.get("stock_status"),
                        weight=float(data.get("weight") or 0),
                        date_created=date_created,
                        date_modified=date_modified,
                    )
                    db.add(product)
            db.commit()
            print(f"✅ Committed page {page}")
        except Exception as e:
            db.rollback()
            print(f"❌ Failed to save products from page {page}: {e}")
        page += 1