from dotenv import load_dotenv
import os

# 👇 Explicitly load from parent directory where .env is located
env_path = os.path.join(os.path.dirname(__file__), '..', '.env')
print("Loading .env from:", os.path.abspath(env_path))
load_dotenv(dotenv_path=os.path.abspath(env_path))
# Force overwrite of environment variable
os.environ["DATABASE_URL"] = os.getenv("DATABASE_URL")
print("Loaded DATABASE_URL:", os.getenv("DATABASE_URL"))
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from crm_backend.models import Base 

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 🚀 THIS creates the tables if they don't exist
# Base.metadata.create_all(bind=engine)


# ✅ Add this missing function
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()