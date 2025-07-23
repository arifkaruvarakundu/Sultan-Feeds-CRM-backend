import requests, json, os
from langchain.prompts import PromptTemplate
from langchain_mistralai.chat_models import ChatMistralAI
from langchain.chains import LLMChain

# MISTRAL_API_KEY = "ZcyCXrqjBgrbCKzm04q65YGxxi5h48Z0"
# os.environ["MISTRAL_API_KEY"] = MISTRAL_API_KEY

WHATSAPP_API_URL = "https://graph.facebook.com/v15.0/730945363428548/messages"
WHATSAPP_ACCESS_TOKEN = "EAAclFm5xlPUBPDCKTpfOhUlmBe7zLTgCH0RUS0gNlc3qvLUBMlnWmHJa5qIVpKn3GLgAFP9tjgIJloJzZCHpFuxJfJ70fKpjBX8PtOL3s9Bl8ceLG7AnvXiGB9gio9Xv3kEnBquIReBR3TJZBVMTTSM0fKnjtOgvuGYkFct0vQrBcCfmGC2jyehsPknuU6z4i7kUK5z10wa8YFjNa9jUvbyBv7gvJBqZBz42i9E"

def send_whatsapp_template(phone_number: str, customer_name: str, order_number: str, template_name: str):
    url = f"https://graph.facebook.com/v18.0/730945363428548/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": phone_number,
        "type": "template",
        "template": {
            "name": template_name,
            "language": { "code": "en" },  # or "ar"
            "components": [
                {
                    "type": "body",
                    "parameters": [
                        { "type": "text", "text": customer_name },
                        { "type": "text", "text": order_number }
                    ]
                }
            ]
        }
    }

    response = requests.post(url, headers=headers, json=payload)
    if response.status_code == 200:
        print(f"✅ WhatsApp message sent using template '{template_name}'")
    else:
        print(f"❌ Failed to send message: {response.status_code} {response.text}")
