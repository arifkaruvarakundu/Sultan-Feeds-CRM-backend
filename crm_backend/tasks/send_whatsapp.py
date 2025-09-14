import requests, json, os, time
from langchain.prompts import PromptTemplate
from langchain_mistralai.chat_models import ChatMistralAI
from langchain.chains import LLMChain
from dotenv import load_dotenv

load_dotenv()

WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_API_URL = f"https://graph.facebook.com/v18.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"

def send_whatsapp_template(phone_number: str, customer_name: str, order_number: str, template_name: str):
    # url = WHATSAPP_API_URL
    # headers = {
    #     "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
    #     "Content-Type": "application/json"
    # }

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

def send_whatsapp_template_message(to: str, template_name: str, variables: list[str], language: str = "en_US") -> dict:
    """
    Send a pre-approved WhatsApp template message.
    :param to: recipient phone number in international format without "+".
    :param template_name: name of your approved template.
    :param variables: list of variables to fill in template placeholders ({{1}}, {{2}}, etc.).
    :param language: template language (default: en_US).
    """
    url = WHATSAPP_API_URL
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }

    # WhatsApp template parameters
    parameters = [{"type": "text", "text": str(v)} for v in variables]

    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language},
            "components": [
                {
                    "type": "body",
                    "parameters": parameters
                }
            ]
        }
    }

    print("[DEBUG] WhatsApp request payload:", json.dumps(payload, ensure_ascii=False))
    t0 = time.time()

    response = requests.post(url, headers=headers, json=payload)

    elapsed = time.time() - t0

    try:
        res_json = response.json()
    except Exception:
        res_json = response.text

    print(f"[DEBUG] WhatsApp response status_code={response.status_code} elapsed={elapsed:.2f}s body={json.dumps(res_json, ensure_ascii=False)}")

    if response.status_code not in (200, 201):
        print("[ERROR] WhatsApp API error:", res_json)
    else:
        print("[INFO] WhatsApp API response:", res_json)

    return res_json
