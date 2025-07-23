# main.py
import os
from fastapi import FastAPI
from crm_backend.routers import sync, auth, orders, products, customers, ai_chat
import redis
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# CORS configuration
origins = [
    "http://localhost:5173",  # your frontend
    "http://127.0.0.1:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,            # or ["*"] if testing locally
    allow_credentials=True,
    allow_methods=["*"],              # allow all HTTP methods
    allow_headers=["*"],              # allow all headers
)

# Redis connection (for example/demo purposes)
redis_host = os.getenv("REDIS_HOST", "localhost")
redis_port = int(os.getenv("REDIS_PORT", 6379))
r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)

# Include your routers
app.include_router(sync.router)
app.include_router(auth.router)
app.include_router(orders.router)
app.include_router(products.router)
app.include_router(customers.router)
app.include_router(ai_chat.router)

@app.get("/")
def read_root():
    r.set("message", "Hello from Redis!")
    return {"message": "Hello, FastAPI!"}

@app.on_event("startup")
def on_startup():
    print("✅ FastAPI app started. Background syncing is managed by Celery + Beat.")
