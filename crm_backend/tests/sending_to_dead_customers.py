from datetime import datetime
from sqlalchemy.orm import Session
from crm_backend.database import get_db
from crm_backend.tasks.sending_to_dead_customers import helper_function_to_sending_message_to_dead_customers

if __name__ == "__main__":
    # Set up DB session
    db: Session = next(get_db())

    # Always run immediately
    print(f"🚀 Running dead customer message sender at {datetime.now()}")

    results = helper_function_to_sending_message_to_dead_customers(db, language="en")
    for r in results:
        print(r)

    print("✅ Finished sending dead customer messages")

