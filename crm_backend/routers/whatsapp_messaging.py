from fastapi import Request, APIRouter, Query, Depends
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os
import re
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio
from sqlalchemy.orm import Session
from crm_backend.models import WhatsAppMessage, Customer, WhatsAppTemplate
from crm_backend.database import get_db
from datetime import datetime
from typing import List
from crm_backend.schemas.templates import SendMessageRequest
from crm_backend.tasks.send_whatsapp import send_whatsapp_template_message
from crm_backend.tasks.reorder_messaging import format_kuwait_number

active_connections = []

load_dotenv()

router = APIRouter()

# 📩 Payload model for sending message
class WhatsAppMessageRequest(BaseModel):
    to_number: str  # e.g. 201234567890 (no +)
    message: str

def normalize_number(number: str) -> str:
    """Remove + and leading zeros for consistent comparison."""
    return number.lstrip("+").lstrip("0")

@router.post("/webhook")
async def whatsapp_webhook(request: Request, db: Session = Depends(get_db)):
    data = await request.json()
    print("📩 [WEBHOOK RECEIVED] Raw payload:", data)

    value = data.get("entry", [{}])[0].get("changes", [{}])[0].get("value", {})
    messages = value.get("messages", [])
    statuses = value.get("statuses", [])

    # ✅ Handle incoming messages
    if messages:
        msg = messages[0]
        from_number = normalize_number(msg.get("from", ""))
        body = msg.get("text", {}).get("body", "")
        timestamp = msg.get("timestamp", None)
        wa_msg_id = msg.get("id")

        print(f"📨 [MESSAGE RECEIVED] from={from_number} text={body} id={wa_msg_id}")

        if timestamp:
            timestamp = datetime.fromtimestamp(int(timestamp))

        # Lookup customer
        customers = db.query(Customer).all()
        matched_customer = None
        for c in customers:
            if normalize_number(c.phone).endswith(from_number[-8:]):
                matched_customer = c
                break

        if matched_customer:
            print(f"✅ [CUSTOMER MATCHED] id={matched_customer.id} phone={matched_customer.phone}")
            db_msg = WhatsAppMessage(
                customer_id=matched_customer.id,
                direction="incoming",
                message=body,
                timestamp=timestamp or datetime.utcnow(),
                whatsapp_message_id=wa_msg_id,
                status=None,
            )
            db.add(db_msg)
            db.commit()
            print("💾 [DB SAVED] Incoming message stored")
        else:
            print("⚠️ [NO CUSTOMER MATCH] Could not match number:", from_number)

    # ✅ Handle message status updates
    if statuses:
        status_event = statuses[0]
        wa_msg_id = status_event.get("id")
        status_type = status_event.get("status")
        timestamp = status_event.get("timestamp")

        print(f"🔔 [STATUS UPDATE] id={wa_msg_id} status={status_type}")

        if timestamp:
            timestamp = datetime.fromtimestamp(int(timestamp))

        db_msg = db.query(WhatsAppMessage).filter(
            WhatsAppMessage.whatsapp_message_id == wa_msg_id
        ).first()

        if db_msg:
            db_msg.status = status_type
            db_msg.timestamp = timestamp or db_msg.timestamp
            db.commit()
            print("💾 [DB UPDATED] Status updated")
        else:
            print("⚠️ [STATUS UPDATE FAILED] No matching message found")

    # ✅ Broadcast to WebSocket clients
    disconnected = []
    for conn in active_connections:
        try:
            await conn.send_json(data)
            print("📡 [WS SENT] Payload pushed to client")
        except Exception as e:
            print("❌ [WS ERROR] Failed to send:", e)
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
    print(f"🔌 [WS CONNECTED] Total clients: {len(active_connections)}")

    try:
        while True:
            # Just keep connection alive
            await asyncio.sleep(10)
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        print(f"❌ [WS DISCONNECTED] Total clients: {len(active_connections)}")
    except Exception as e:
        print(f"⚠️ [WS ERROR] {e}")
        if websocket in active_connections:
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

def fill_template(body: str, values: list[str] | None = None) -> str:
    """
    Replace numbered placeholders {{1}}, {{2}}, ... with provided values.
    """
    message = body
    if values:
        for idx, val in enumerate(values, start=1):
            message = re.sub(rf"{{{{{idx}}}}}", str(val), message)
    return message

# @router.post("/send-message-to-each-customer")
# def send_message(data: SendMessageRequest):
#     if not data.customers:
#         raise HTTPException(status_code=400, detail="No customers selected")
#     if not data.templates:
#         raise HTTPException(status_code=400, detail="No templates selected")

#     target_customers = [c for c in CUSTOMERS_DB if c["id"] in data.customers]
#     if not target_customers:
#         raise HTTPException(status_code=404, detail="No valid customers found")

#     messages = []
#     for customer in target_customers:
#         for template in data.templates:
#             values = data.variables.get(customer["id"], []) if data.variables else []
#             filled = fill_template(template.body, values)
#             msg = {
#                 "to": customer["phone"],
#                 "name": customer["name"],
#                 "template": template.template_name,
#                 "message": filled,
#             }
#             messages.append(msg)

#             # 👉 Replace this with actual send logic (Twilio, WhatsApp API, etc.)
#             print(f"Sending to {customer['phone']}: {filled}")

#     return {
#         "status": "success",
#         "sent": len(messages),
#         "messages": messages,
#     }

TEMPLATE_VARIABLE_MAPPING = {
    "order_delivered": ["full_name", "external_id"],
    "delivery_confirmation_2": ["full_name", "external_id"],
    "dead_customers_message": ["full_name"],
    "dead_customer_message_ar": ["full_name"],
    "example_for_quick_reply": ["full_name"],
    "order_onhold": ["full_name", "external_id"],
    "order_management_1": ["full_name"]
}

def customer_to_dict(customer: Customer) -> dict:
    """Convert SQLAlchemy Customer object into a dict with customer + latest order fields (no address)."""
    data = {
        "id": customer.id,
        "first_name": customer.first_name,
        "last_name": customer.last_name,
        "full_name": f"{customer.first_name} {customer.last_name}",
        "email": customer.email,
        "phone": customer.phone,
    }

    # Include the latest order (if exists)
    if customer.orders:
        latest_order = sorted(customer.orders, key=lambda o: o.created_at, reverse=True)[0]
        data.update({
            "external_id": latest_order.external_id,
            "order_status": latest_order.status,
            "order_total": latest_order.total_amount,
        })

    return data

def get_template_variables(cust_dict: dict, template_name: str) -> list[str]:
    """
    Returns a list of values for a template.
    If a field is missing in cust_dict, replaces with empty string.
    """
    fields = TEMPLATE_VARIABLE_MAPPING.get(template_name, [])
    values = [str(cust_dict.get(f, "")) for f in fields]
    return values

@router.post("/send-message-to-each-customer")
def send_message(data: SendMessageRequest, db: Session = Depends(get_db)):

    print("📩 API /send-message-to-each-customer was called!")
    print("Received payload:", data.dict())

    if not data.customers:
        raise HTTPException(status_code=400, detail="No customers selected")
    if not data.templates:
        raise HTTPException(status_code=400, detail="No templates selected")

    # Fetch customers from DB
    target_customers = db.query(Customer).filter(Customer.id.in_(data.customers)).all()
    if not target_customers:
        raise HTTPException(status_code=404, detail="No valid customers found")

    # Fetch templates
    db_templates = db.query(WhatsAppTemplate).filter(
        WhatsAppTemplate.template_name.in_(data.templates)
    ).all()
    if not db_templates:
        raise HTTPException(status_code=404, detail="No valid templates found")

    messages = []

    for customer in target_customers:
        cust_dict = customer_to_dict(customer)

        for tpl in db_templates:
            # Numbered placeholders via mapping
            # numbered_fields = TEMPLATE_VARIABLE_MAPPING.get(tpl.template_name, [])
            # numbered_values = get_template_variables(cust_dict, tpl.template_name)
            placeholder_count = len(tpl.variables)

            # get field names from mapping (fallback)
            field_names = TEMPLATE_VARIABLE_MAPPING.get(tpl.template_name, [])

            # build values based on detected placeholder count
            numbered_values = []
            for i in range(placeholder_count):
                if i < len(field_names):
                    field = field_names[i]
                    numbered_values.append(str(cust_dict.get(field, "")))
                else:
                    # fallback if mapping missing
                    numbered_values.append("")
            # ✅ validation (skip if all values are empty)
            if not any(v.strip() for v in numbered_values):
                print(f"⚠️ Skipping {tpl.template_name} for {cust_dict['id']} - no valid variables")
                continue

            formatted_phone = format_kuwait_number(cust_dict["phone"])

            # Send via WhatsApp template API
            msg_response = send_whatsapp_template_message(
                to=formatted_phone,
                template_name=tpl.template_name,
                variables=numbered_values,
                language=tpl.language
            )
            messages.append(msg_response)
            print(f"Sent to {cust_dict['phone']}: {numbered_values}")

    return {
            "status": "success",
            "sent": len(messages),
            "messages": messages,
        }    
