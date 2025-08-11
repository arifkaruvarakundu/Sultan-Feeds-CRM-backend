from crm_backend.database import SessionLocal
from crm_backend.tasks.whatsapp_msg_after_one_month import get_customers_since

# db = SessionLocal()
# customers = get_customers_since(db)
# print(customers)

# def send_whatsapp_message_after_one_month(db):
#     # customers = get_customers_since(db)
#     customers = [{'customer_name': 'Muhammed Harif', 'phone_number': '919745674674'}]
#     for row in customers:
#         customer_name = row["customer_name"]
#         phone_number = row["phone_number"]
        
#         # Force sending for testing
#         status, result = send_whatsapp_reorder_reminder_after_one_month(
#             phone_number, customer_name, "en"
#         )
#         print(f"Sent to {customer_name} ({phone_number}): {status} - {result}")

from crm_backend.database import SessionLocal
from crm_backend.tasks.whatsapp_msg_after_one_month import get_customers_since, send_whatsapp_reorder_reminder_after_one_month

def send_whatsapp_message_after_one_month(db, test_mode=True):
    if test_mode:
        customers = [{'customer_name': 'Muhammed Harif', 'phone_number': '919745674674'}]
    else:
        customers = get_customers_since(db)

    for row in customers:
        customer_name = row["customer_name"]
        phone_number = row["phone_number"]

      # Send English
        status_en, result_en = send_whatsapp_reorder_reminder_after_one_month(
            phone_number, customer_name, "en"
        )
        print(f"[EN] Sent to {customer_name} ({phone_number}): {status_en} - {result_en}")

        # Send Arabic
        status_ar, result_ar = send_whatsapp_reorder_reminder_after_one_month(
            phone_number, customer_name, "ar"
        )
        print(f"[AR] Sent to {customer_name} ({phone_number}): {status_ar} - {result_ar}")

if __name__ == "__main__":
    db = SessionLocal()
    send_whatsapp_message_after_one_month(db, test_mode=True)  # Switch to False for DB mode
