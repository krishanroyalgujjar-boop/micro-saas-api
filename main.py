import os
import redis
from fastapi import FastAPI, Header, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests

app = FastAPI(title="AI Micro-SaaS API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment Variables se Credentials uthana
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

# Redis Connection setup
r = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    password=REDIS_PASSWORD,
    ssl=True,
    decode_responses=True
)

class RefineRequest(BaseModel):
    raw_text: str

@app.get("/")
def home():
    return {"status": "API is running successfully ⚡"}

@app.post("/v1/auth/create-key")
def create_api_key(email: str = Query(...)):
    import uuid
    api_key = f"sk_live_{uuid.uuid4().hex}"
    
    # Store initial wallet balance: ₹10 free trial
    r.set(f"wallet:{api_key}", 10.0)
    r.set(f"email:{api_key}", email)
    
    return {
        "api_key": api_key,
        "welcome_balance_inr": 10.0,
        "message": "API key generated successfully with ₹10 free trial!"
    }

@app.post("/v1/refine")
def refine_text(payload: RefineRequest, x_api_key: str = Header(...)):
    # 1. Verify API Key in Redis
    balance = r.get(f"wallet:{x_api_key}")
    if balance is None:
        raise HTTPException(status_code=401, detail="Invalid API Key")
    
    current_balance = float(balance)
    cost_per_call = 1.00  # ₹1 per call
    
    if current_balance < cost_per_call:
        raise HTTPException(status_code=402, detail="Insufficient Balance! Please top up your wallet.")
    
    # 2. Call Groq AI Llama 3 Model
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    ai_payload = {
        "model": "llama3-8b-8192",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that converts raw messy text into clean structured JSON format only."},
            {"role": "user", "content": payload.raw_text}
        ],
        "temperature": 0.1
    }
    
    try:
        response = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=ai_payload)
        res_data = response.json()
        ai_output = res_data["choices"][0]["message"]["content"]
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI Model Error: {str(e)}")
    
    # 3. Deduct Balance from Redis Wallet
    new_balance = current_balance - cost_per_call
    r.set(f"wallet:{x_api_key}", new_balance)
    
    return {
        "deducted_inr": cost_per_call,
        "remaining_balance_inr": new_balance,
        "data": ai_output
    }
