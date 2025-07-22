import requests, json, os
from langchain.prompts import PromptTemplate
from langchain_mistralai.chat_models import ChatMistralAI
from langchain.chains import LLMChain

MISTRAL_API_KEY = "ZcyCXrqjBgrbCKzm04q65YGxxi5h48Z0"
os.environ["MISTRAL_API_KEY"] = MISTRAL_API_KEY

# WHATSAPP_API_URL = "https://graph.facebook.com/v15.0/730945363428548/messages"
# WHATSAPP_ACCESS_TOKEN = "EAAclFm5xlPUBPDCKTpfOhUlmBe7zLTgCH0RUS0gNlc3qvLUBMlnWmHJa5qIVpKn3GLgAFP9tjgIJloJzZCHpFuxJfJ70fKpjBX8PtOL3s9Bl8ceLG7AnvXiGB9gio9Xv3kEnBquIReBR3TJZBVMTTSM0fKnjtOgvuGYkFct0vQrBcCfmGC2jyehsPknuU6z4i7kUK5z10wa8YFjNa9jUvbyBv7gvJBqZBz42i9E"

# HEADERS = {
#     "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
#     "Content-Type": "application/json"
# }

# llm = ChatMistralAI(model="mistral-medium-2505", temperature=0.7)

# # prompt = PromptTemplate(
# #     input_variables=["name", "classification", "total_spent", "last_order_date", "tone", "goal"],
# #     template=(
# #         "اكتب رسالة واتساب بأسلوب {tone} لهدف {goal}.\n"
# #         "الاسم: {name}\n"
# #         "التصنيف: {classification}\n"
# #         "الإنفاق الكلي: {total_spent} ريال\n"
# #         "آخر طلب: {last_order_date}\n"
# #         "ابدأ الرسالة الآن:"
# #     )
# # )

# prompt = PromptTemplate(
#     input_variables=["name", "classification", "total_spent", "last_order_date", "tone", "goal"],
#     template=(
#         "اكتب رسالة واتساب بأسلوب {tone} لهدف {goal}.\n"
#         "الاسم: {name}\n"
#         "التصنيف: {classification}\n"
#         "الإنفاق الكلي: {total_spent} ريال\n"
#         "آخر طلب: {last_order_date}\n"
#         "- يجب أن تتضمن الرسالة:\n"
#         "- افتتاحية شخصية\n"
#         "- عرض أو دعوة واضحة مرتبطة بهدف {goal}\n"
#         "- حث على اتخاذ إجراء\n"
#         "- لمسة ودية في الختام\n"
#         "ابدأ الرسالة الآن:"
#     )
# )

# chain = prompt | llm

# CUSTOMER_API = "http://127.0.0.1:8000/full-customer-classification"

# def fetch_customers():
#     response = requests.get(CUSTOMER_API)
#     return response.json()

# # def select_tone_and_goal(customer):
# #     churn = customer["churn_risk"]
# #     if churn == "High":
# #         return ("ودّي", "استرجاع")
# #     elif churn == "Medium":
# #         return ("مهني", "تحفيز")
# #     else:
# #         return ("احتفالي", "شكر")

# def select_tone_and_goal(customer):
#     churn = customer["churn_risk"]
#     classification = customer["classification"]

#     if churn == "High":
#         return ("ودّي", "إعادة تفعيل العميل")
#     elif churn == "Medium":
#         if classification == "Potential VIP":
#             return ("مهني", "تحفيز الشراء بمزايا حصرية")
#         else:
#             return ("مهني", "تقديم عرض محفز للشراء")
#     else:
#         return ("احتفالي", "شكر العميل وتقديم مكافأة ولاء")

# def send_whatsapp(to_number, body_text):
#     payload = {
#         "messaging_product": "whatsapp",
#         "to": to_number,
#         "type": "text",
#         "text": { "body": body_text }
#     }

#     response = requests.post(
#         WHATSAPP_API_URL,
#         headers=HEADERS,
#         data=json.dumps(payload)
#     )

#     print(f"[WhatsApp] Status: {response.status_code}")
#     print(f"[WhatsApp] Response: {response.text}")

# def generate_and_send_messages():
#     customers = fetch_customers()
#     for customer in customers:
#         name = customer["customer_name"]
#         classification = customer["classification"]
#         total_spent = customer["total_spent"]
#         last_order_date = customer["last_order_date"]

#         tone, goal = select_tone_and_goal(customer)

#         msg = chain.invoke({
#             "name": name,
#             "classification": classification,
#             "total_spent": total_spent,
#             "last_order_date": last_order_date,
#             "tone": tone,
#             "goal": goal
#         })

#         text = msg.content if hasattr(msg, "content") else str(msg)

#         to_number = customer.get("phone")
#         if to_number:
#             send_whatsapp(to_number, text)

#     return {"status": "messages sent"}

def generate_whatsapp_message(data):
    prompt = f"""
    Write a short personalized WhatsApp message for a customer:
    - Name: {data['customer_name']}
    - Last order date: {data['last_order_date']}
    - Orders made: {data['order_count']}
    - Total spent: KD {data['total_spent']}
    - Classification: {data['classification']}
    - Spending pattern: {data['spending_classification']}
    - Churn risk: {data['churn_risk']}
    - Segment: {data['segment']}

    The tone should be warm and encouraging. You can express gratitude depending on their segment. End with a friendly call to action in Arabic.
    """

    response = requests.post(
        "https://api.mistral.ai/v1/chat/completions",
        headers={
            "Authorization": f"Bearer {MISTRAL_API_KEY}",
            "Content-Type": "application/json"
        },
        json={
            "model": "mistral-medium",
            "messages": [{"role": "user", "content": prompt}]
        }
    )

    return response.json()["choices"][0]["message"]["content"]

def send_whatsapp_message(phone_number, message):
    url = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": f"965{phone_number}",  # Assuming Kuwait
        "type": "text",
        "text": {"body": message}
    }

    response = requests.post(url, headers=headers, json=payload)
    return response.status_code, response.json()


def run_campaign():
    # 1. Fetch customer behavior data
    response = requests.get("https://your-api.com/customer-insights")
    customers = response.json()

    for customer in customers:
        try:
            if customer.get("phone") and customer.get("customer_name"):
                # 2. Generate message
                message = generate_whatsapp_message(customer)
                print(f"Generated for {customer['customer_name']}: {message}")

                # 3. Send via WhatsApp
                status, result = send_whatsapp_message(customer["phone"], message)
                print(f"Sent to {customer['phone']}: {status} | {result}")
        except Exception as e:
            print(f"Failed for {customer['customer_id']}: {e}")