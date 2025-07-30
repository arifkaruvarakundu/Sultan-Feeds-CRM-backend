# import requests, json, os
# from langchain.prompts import PromptTemplate
# from langchain_mistralai.chat_models import ChatMistralAI
# from langchain.chains import LLMChain

# MISTRAL_API_KEY = "your-api-key"
# os.environ["MISTRAL_API_KEY"] = MISTRAL_API_KEY

# WHATSAPP_API_URL = "https://graph.facebook.com/v15.0/730945363428548/messages"
# WHATSAPP_ACCESS_TOKEN = "your-whatsapp-token"

# HEADERS = {
#     "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
#     "Content-Type": "application/json"
# }

# llm = ChatMistralAI(model="mistral-medium-2505", temperature=0.7)

# prompt = PromptTemplate(
#     input_variables=["name", "classification", "total_spent", "last_order_date", "tone", "goal"],
#     template=(
#         "اكتب رسالة واتساب بأسلوب {tone} لهدف {goal}.\n"
#         "الاسم: {name}\n"
#         "التصنيف: {classification}\n"
#         "الإنفاق الكلي: {total_spent} ريال\n"
#         "آخر طلب: {last_order_date}\n"
#         "ابدأ الرسالة الآن:"
#     )
# )

# chain = prompt | llm

# CUSTOMER_API = "http://127.0.0.1:8000/full-customer-classification"

# def fetch_customers():
#     response = requests.get(CUSTOMER_API)
#     return response.json()

# def select_tone_and_goal(customer):
#     churn = customer["churn_risk"]
#     if churn == "High":
#         return ("ودّي", "استرجاع")
#     elif churn == "Medium":
#         return ("مهني", "تحفيز")
#     else:
#         return ("احتفالي", "شكر")

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
