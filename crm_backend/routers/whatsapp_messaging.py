from fastapi import Request, APIRouter, Query
from fastapi.responses import PlainTextResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
import requests
import os
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import asyncio

active_connections = []

load_dotenv()

router = APIRouter()

# 📩 Payload model for sending message
class WhatsAppMessageRequest(BaseModel):
    to_number: str  # e.g. 201234567890 (no +)
    message: str

# 🔔 Webhook POST
# @router.post("/webhook")
# async def whatsapp_webhook(request: Request):
#     data = await request.json()
#     print("Received:", data)
#     return {"status": "received"}

# @router.post("/webhook")
# async def whatsapp_webhook(request: Request):
#     data = await request.json()
#     print("Received:", data)

#     for ws in active_connections:
#         await ws.send_json(data)  # forward to connected frontends

#     return {"status": "received"}


# @router.post("/webhook")
# async def whatsapp_webhook(request: Request):
#     data = await request.json()
#     print("📩 Webhook Received:", data)

#     # Extract actual message text (depends on WhatsApp's structure)
#     try:
#         message_text = data["entry"][0]["changes"][0]["value"]["messages"][0]["text"]["body"]
#     except (KeyError, IndexError):
#         message_text = "[unknown format]"

#     disconnected = []
#     for conn in active_connections:
#         try:
#             await conn.send_json({"body": message_text})
#         except Exception as e:
#             print("❌ Failed to send to WebSocket:", e)
#             disconnected.append(conn)

#     # Remove disconnected clients
#     for conn in disconnected:
#         active_connections.remove(conn)

#     return {"status": "received"}

@router.post("/webhook")
async def whatsapp_webhook(request: Request):
    data = await request.json()
    print("📩 Webhook Received:", data)

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
def send_message(data: WhatsAppMessageRequest):
    try:
        result = send_whatsapp_message(data.to_number, data.message)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

###
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            await asyncio.sleep(1)  # optional, can be ping
    except WebSocketDisconnect:
        active_connections.remove(websocket)