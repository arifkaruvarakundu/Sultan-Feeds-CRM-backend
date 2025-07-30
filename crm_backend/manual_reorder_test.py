# # manual_reorder_test.py

# from crm_backend.tasks.reorder_messaging import predict_customers_to_remind, send_reorder_reminders_to_customers, get_customer_info

# # Step 1: Predict customers
# customer_ids = predict_customers_to_remind()
# print(f"🔮 Predicted {len(customer_ids)} customers for reorder reminder.")

# # Step 2: Print detailed info
# for cid in customer_ids:
#     customer = get_customer_info(cid)
#     if customer:
#         print(f"👤 ID: {cid}, Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone}")

# # Step 3: Optionally, send messages to test
# print("\n📲 Sending WhatsApp messages to predicted customers...")
# send_reorder_reminders_to_customers(customer_ids)

# manual_reorder_test.py

from crm_backend.tasks.reorder_messaging import send_reorder_reminders_to_customers, get_customer_info

# 🔧 Manually specify one customer ID for testing
test_customer_id = 5217 # Replace with a real customer ID from your database
customer = get_customer_info(test_customer_id)

if customer:
    print(f"👤 Testing for ID: {test_customer_id}, Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone}")
    print("\n📲 Sending WhatsApp messages to the test customer...")
    send_reorder_reminders_to_customers([test_customer_id])
else:
    print(f"❌ No customer found with ID {test_customer_id}")
