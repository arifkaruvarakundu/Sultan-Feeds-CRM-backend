# main.py
import os
from fastapi import FastAPI
from crm_backend.routers import sync, auth, orders, products, customers, ai_chat, whatsapp_messaging, forecast_api, csv_analysis
import redis
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware

load_dotenv()

app = FastAPI()

# CORS configuration
origins = [
    "https://crm.souqalsultan.com",
    "https://sultan-feeds-crm-frontend-git-main-muhammed-harifs-projects.vercel.app",
    "http://localhost:5173", 
    "http://localhost:5174"
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
app.include_router(whatsapp_messaging.router)
app.include_router(forecast_api.router)
app.include_router(csv_analysis.router)

@app.get("/")
def read_root():
    r.set("message", "Hello from Redis!")
    return {"message": "Hello, FastAPI!"}

@app.on_event("startup")
def on_startup():
    print("✅ FastAPI app started. Background syncing is managed by Celery + Beat.")
