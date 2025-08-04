from fastapi import Request, APIRouter, Query, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio
from sqlalchemy.orm import Session
from crm_backend.models import WhatsAppMessage, Customer
from crm_backend.database import get_db
from datetime import datetime
from typing import List

active_connections = []

load_dotenv()

router = APIRouter()

# 📩 Payload model for sending message
class WhatsAppMessageRequest(BaseModel):
    to_number: str  # e.g. 201234567890 (no +)
    message: str

@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    print("📩 Webhook Received:", data)

    value = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
    messages = value.get("messages", [])
    statuses = value.get("statuses", [])

    if messages:
        msg = messages[0]
        from_number = msg.get("from")
        body = msg.get("text", {}).get("body", "")
        timestamp = msg.get("timestamp", None)
        wa_msg_id = msg.get("id")

        if timestamp:
            timestamp = datetime.fromtimestamp(int(timestamp))

        # 📌 Lookup customer by phone
        customer = db.query(Customer).filter(Customer.phone.contains(from_number[-8:])).first()

        if customer:
            db_msg = WhatsAppMessage(
                customer_id=customer.id,
                direction="incoming",
                message=body,
                timestamp=timestamp or datetime.utcnow(),
                whatsapp_message_id=wa_msg_id,
                status = None
            )
            db.add(db_msg)
            db.commit()
    
     # ✅ Handle message status updates (sent/delivered/read)
    if statuses:
        status_event = statuses[0]
        wa_msg_id = status_event.get("id")
        status_type = status_event.get("status")  # e.g., "delivered", "read"
        timestamp = status_event.get("timestamp")

        if timestamp:
            timestamp = datetime.fromtimestamp(int(timestamp))

        # ✅ FIXED: Use whatsapp_message_id, not id
        db_msg = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.whatsapp_message_id == wa_msg_id
        ).first()

        if db_msg:
            db_msg.status = status_type
            db_msg.timestamp = timestamp or db_msg.timestamp
            db.commit()

    disconnected = []
    for conn in active_connections:
        try:
            await conn.send_json(data)  # ✅ send entire webhook payload
        except Exception as e:
            print("❌ Failed to send to WebSocket:", e)
            disconnected.append(conn)

    for conn in disconnected:
        active_connections.remove(conn)

    return {"status": "received"}

# 🌐 Webhook GET (verification)
@router.get("/webhook")
def verify_webhook(
    hub_mode: str = Query(..., alias="hub.mode"),
    hub_challenge: str = Query(..., alias="hub.challenge"),
    hub_verify_token: str = Query(..., alias="hub.verify_token"),
):
    if hub_mode == "subscribe" and hub_verify_token == "harif313":
        return PlainTextResponse(hub_challenge)
    return PlainTextResponse("Verification failed", status_code=403)

# 📤 WhatsApp Config
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")

WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

# 📨 Message Sender
def send_whatsapp_message(to_number: str, message: str):
    url = WHATSAPP_API_URL
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {
            "body": message
        }
    }
    response = requests.post(url, headers=headers, json=payload)
    print("✅ Message sent:", response.json())
    return response.json()

# 🔗 New endpoint: Send message via API
@router.post("/send-message")
def send_message(data: WhatsAppMessageRequest, db: Session = Depends(get_db)):
    try:
        result = send_whatsapp_message(data.to_number, data.message)

        # Get the customer from the DB
        customer = db.query(Customer).filter(Customer.phone.contains(data.to_number[-8:])).first()

        if customer:
            db_msg = WhatsAppMessage(
                customer_id=customer.id,
                direction="outgoing",
                message=data.message,
                timestamp=datetime.utcnow(),
                status="sent"
            )
            db.add(db_msg)
            db.commit()

        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # optional, can be ping
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@router.get("/whatsapp-messages", response_model=List[dict])
def get_messages(phone: str, db: Session = Depends(get_db)):
    customer = db.query(Customer).filter(Customer.phone == phone).first()
    if not customer:
        return []

    messages = (
        db.query(WhatsAppMessage)
        .filter(WhatsAppMessage.customer_id == customer.id)
        .order_by(WhatsAppMessage.timestamp.asc())
        .all()
    )

    return [
        {
            "id": m.id,
            "text": m.message,
            "from": "me" if m.direction == "outgoing" else "them",
            "timestamp": m.timestamp.timestamp(),  # convert to epoch for JS
            "status": "sent" if m.direction == "outgoing" else None,
        }
        for m in messages
    ]

# @router.get()