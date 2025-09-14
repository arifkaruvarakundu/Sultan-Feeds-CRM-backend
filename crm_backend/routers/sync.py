# crm_backend/routers/sync.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from crm_backend.database import SessionLocal
# from utils.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_products import fetch_and_save_products
from dotenv import load_dotenv
from crm_backend.models import WhatsAppTemplate
import os
import requests
from datetime import datetime
from typing import List
from crm_backend.schemas.templates import WhatsAppTemplateBase

router = APIRouter()

load_dotenv()

ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WABA_ID = os.getenv("WABA_ID")

# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.post("/sync-orders/")
def trigger_sync_all():
    fetch_and_save_orders()
    return {"message": "Order sync task dispatched"}

@router.post("/sync-products/")
def trigger_sync_all():
    fetch_and_save_products()
    return {"message": "Product sync task dispatched"}

@router.post("/sync-templates")
def sync_templates(db: Session = Depends(get_db)):
    url = f"https://graph.facebook.com/v20.0/{WABA_ID}/message_templates"
    headers = {"Authorization": f"Bearer {ACCESS_TOKEN}"}
    response = requests.get(url, headers=headers)

    if response.status_code != 200:
        return {"error": response.json()}

    templates = response.json().get("data", [])

    for t in templates:
        body_component = next((c for c in t.get("components", []) if c["type"] == "BODY"), {})
        
        # UPSERT logic using SQLAlchemy ORM
        existing = db.query(WhatsAppTemplate).filter_by(template_name=t["name"]).first()
        if existing:
            existing.category = t["category"]
            existing.language = t["language"]
            existing.status = t["status"]
            existing.body = body_component.get("text")
            existing.updated_at = datetime.utcnow()
        else:
            new_template = WhatsAppTemplate(
                template_name=t["name"],
                category=t["category"],
                language=t["language"],
                status=t["status"],
                body=body_component.get("text"),
                updated_at=datetime.utcnow()
            )
            db.add(new_template)

    db.commit()

    return {"message": f"✅ Synced {len(templates)} templates"}

@router.get("/templates/", response_model=List[WhatsAppTemplateBase])
def get_templates(db: Session = Depends(get_db)):

    templates = db.query(WhatsAppTemplate).all()

    return templates