import os
import json
import secrets
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import redis
import requests

app = FastAPI(title="Micro-SaaS AI Refiner API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

REDIS_HOST = os.getenv("REDIS_HOST", "")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    ssl=True,
    decode_responses=True
)

class RefineRequest(BaseModel):
    raw_text: str

@app.post("/v1/auth/create-key")
def create_api_key(email: str):
    new_key = f"sk_live_{secrets.token_hex(12)}"
    r.set(f"key:{new_key}:owner", email)
    r.set(f"balance:{new_key}", 1000) # ₹10 free trial balance (1000 paise)
    return {"api_key": new_key, "welcome_balance_inr": 10.00}

@app.post("/v1/refine")
async def refine_payload(payload: RefineRequest, x_api_key: str = Header(...)):
    COST_PAISE = 100 # ₹1.00 per call
    balance_key = f"balance:{x_api_key}"
    
    if not r.exists(f"key:{x_api_key}:owner"):
        raise HTTPException(status_code=401, detail="Invalid API Key")

    current_balance = r.decrby(balance_key, COST_PAISE)
    
    if current_balance < 0:
        r.incrby(balance_key, COST_PAISE)
        raise HTTPException(status_code=402, detail="Insufficient Balance. Top up via UPI.")

    try:
        groq_response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "llama3-8b-8192",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a JSON converter. Convert raw input text into structured, clean JSON output. Return ONLY valid JSON."
                    },
                    {"role": "user", "content": payload.raw_text}
                ],
                "response_format": {"type": "json_object"}
            },
            timeout=10
        )
        ai_data = groq_response.json()["choices"][0]["message"]["content"]
        structured_json = json.loads(ai_data)
    except Exception:
        structured_json = {"raw": payload.raw_text, "status": "processed"}

    return {
        "status": "success",
        "deducted_inr": 1.00,
        "remaining_balance_inr": round(current_balance / 100, 2),
        "data": structured_json
    }

@app.post("/v1/webhooks/razorpay")
async def razorpay_webhook(request: Request):
    data = await request.json()
    if data.get("event") == "payment.captured":
        payment = data["payload"]["payment"]["entity"]
        amount_paid_inr = payment["amount"] / 100
        api_key = payment["notes"].get("api_key")
        
        if api_key and r.exists(f"key:{api_key}:owner"):
            paise_to_add = int(amount_paid_inr * 100)
            new_bal = r.incrby(f"balance:{api_key}", paise_to_add)
            return {"status": "wallet_credited", "new_balance_inr": new_bal / 100}

    return {"status": "ignored"}

@app.get("/")
def health_check():
    return {"status": "online", "engine": "Micro-SaaS Billing Engine v1.0"}
