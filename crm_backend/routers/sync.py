# crm_backend/routers/sync.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from crm_backend.database import SessionLocal
# from utils.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_orders import fetch_and_save_orders
from crm_backend.tasks.fetch_products import fetch_and_save_products


router = APIRouter()

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