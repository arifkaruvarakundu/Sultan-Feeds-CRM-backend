from twilio.rest import Client
from dotenv import load_dotenv
import os
from crm_backend.database import SessionLocal
from crm_backend.models import Customer

load_dotenv()

ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
FROM_WHATSAPP = os.getenv("TWILIO_WHATSAPP_FROM")

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def format_phone_number(number):
    # Add country code if needed, adjust for your use case
    if not number.startswith("+"):
        return "+965" + number.lstrip("0")  # example: Saudi numbers
    return number

def send_whatsapp_message(to, message):
    to = f"whatsapp:{format_phone_number(to)}"
    return client.messages.create(
        body=message,
        from_=FROM_WHATSAPP,
        to=to
    )

def send_whatsapp_to_customers():
    db = SessionLocal()
    try:
        customers = db.query(Customer).all()
        for customer in customers:
            if customer.phone:
                message = f"Hi {customer.first_name}, thank you for your cooperation! This is Sultan Feeds—just checking in to see how your pet is doing. 😊"
                try:
                    send_whatsapp_message(customer.phone, message)
                    print(f"✅ Sent to {customer.phone}")
                except Exception as e:
                    print(f"❌ Failed for {customer.phone}: {str(e)}")
    finally:
        db.close()

# if __name__ == "__main__":
#     test_number = "+919745674674"  # ← Replace with your WhatsApp number
#     test_message = "👋 Hello from FastAPI + Celery + Twilio!"
    
#     try:
#         result = send_whatsapp_message(test_number, test_message)
#         print("✅ Test message sent successfully!")
#         print(result.sid)  # Optional: Twilio message SID
#     except Exception as e:
#         print(f"❌ Error sending message: {e}")
