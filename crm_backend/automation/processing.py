import requests
from your_ai_module import get_tone_and_goal, generate_whatsapp_message_with_ai, send_whatsapp

# 1. Get latest customer classification data
response = requests.get("http://127.0.0.1:8000/full-customer-classification")
customers = response.json()

for customer in customers:
    # 2. Determine tone/goal (can be rule-based or ML model)
    tone, goal, urgency = get_tone_and_goal(customer)

    # 3. Generate personalized message
    message = generate_whatsapp_message_with_ai(customer, tone, goal, urgency)

    # 4. Send via WhatsApp (optional)
    send_whatsapp(customer["customer_id"], customer["customer_name"], message)

    # 5. Log it (optional)
    log_sent_message(customer["customer_id"], message, tone, goal)
