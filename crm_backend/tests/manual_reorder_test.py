# manual_reorder_test.py

# from crm_backend.tasks.reorder_messaging import predict_customers_to_remind, send_reorder_reminders_to_customers, get_customer_info

# # Step 1: Predict customers
# customer_ids = predict_customers_to_remind()
# print(f"🔮 Predicted {len(customer_ids)} customers for reorder reminder.")

# # Step 2: Print detailed info
# for cid in customer_ids:
#     customer = get_customer_info(cid)
#     if customer:
#         print(f"👤 ID: {cid}, Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone}")

# Step 3: Optionally, send messages to test
# print("\n📲 Sending WhatsApp messages to predicted customers...")
# send_reorder_reminders_to_customers(customer_ids)


# manual_reorder_test.py

# from crm_backend.tasks.reorder_messaging import send_reorder_reminders_to_customers, get_customer_info

# # 🔧 Manually specify one customer ID for testing
# test_customer_id = 5217 # Replace with a real customer ID from your database
# customer = get_customer_info(test_customer_id)

# if customer:
#     print(f"👤 Testing for ID: {test_customer_id}, Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone}")
#     print("\n📲 Sending WhatsApp messages to the test customer...")
#     send_reorder_reminders_to_customers([test_customer_id])
# else:
#     print(f"❌ No customer found with ID {test_customer_id}")

# from datetime import date, timedelta
# from crm_backend.tasks.reorder_messaging import predict_customers_to_remind, get_customer_info

# base_date = date(2025, 7, 30)
# results = {}

# # Simulate for 5 consecutive days
# for i in range(5):
#     test_date = base_date + timedelta(days=i)
#     print(f"\n📅 Testing for: {test_date}")
    
#     customer_ids = predict_customers_to_remind(target_date=test_date)
#     results[test_date] = set(customer_ids)

#     for cid in customer_ids:
#         customer = get_customer_info(cid)
#         if customer:
#             print(f"👤 ID: {cid}, Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone}")

# # Compare differences between days
# print("\n🔍 Comparing daily predictions:")
# days = list(results.keys())
# for i in range(len(days) - 1):
#     day1 = days[i]
#     day2 = days[i + 1]
#     diff = results[day1].symmetric_difference(results[day2])
#     print(f"Difference between {day1} and {day2}: {len(diff)} customers")

from datetime import date, timedelta
import pandas as pd
from crm_backend.tasks.reorder_messaging import (
    predict_customers_to_remind,
    get_customer_info
)
from sqlalchemy import create_engine
from crm_backend.customers.operation_helper import function_get_full_customer_classification
from dotenv import load_dotenv
import os
from sqlalchemy.orm import sessionmaker

# Load variables from .env
load_dotenv()

# Read the database URL from .env
DATABASE_URL = os.getenv("DATABASE_URL")

# Create the engine
engine = create_engine(DATABASE_URL)

# Create a session
SessionLocal = sessionmaker(bind=engine)
db_session = SessionLocal()

# 1️⃣ Get the classified customer data
customer_data = function_get_full_customer_classification(db_session)
df = pd.DataFrame(customer_data)

# 2️⃣ Get orders data for Loyal/Frequent gap calculation
orders_df = pd.read_sql(
    "SELECT customer_id, created_at FROM orders WHERE status = 'completed'",
    engine
)
orders_df["created_at"] = pd.to_datetime(orders_df["created_at"])

# 3️⃣ Simulation variables
base_date = date(2025, 7, 30)
results = {}
last_reminded = {}  # ✅ Keep track of reminders across days

# 4️⃣ Simulate for 5 consecutive days with cooldown
for i in range(10):
    test_date = base_date + timedelta(days=i)
    print(f"\n📅 Testing for: {test_date}")

    customer_ids, last_reminded = predict_customers_to_remind(
        df, orders_df, target_date=test_date, last_reminded=last_reminded
    )
    results[test_date] = set(customer_ids)

    for cid in customer_ids:
        customer = get_customer_info(cid)
        if customer:
            print(f"👤 ID: {cid}, Name: {customer.first_name} {customer.last_name}, Phone: {customer.phone}")

# 5️⃣ Compare differences between days
print("\n🔍 Comparing daily predictions:")
days = list(results.keys())
for i in range(len(days) - 1):
    day1 = days[i]
    day2 = days[i + 1]
    diff = results[day1].symmetric_difference(results[day2])
    print(f"Difference between {day1} and {day2}: {len(diff)} customers")

