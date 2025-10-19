from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from motor.motor_asyncio import AsyncIOMotorClient
from passlib.hash import bcrypt
from bson import ObjectId
import random
from datetime import datetime

app = FastAPI()

client = AsyncIOMotorClient("mongodb://localhost:27017")
db = client["postcrossing"]

class User(BaseModel):
    username: str
    email: str
    password: str
    country: str

class Login(BaseModel):
    username: str
    password: str

class Send(BaseModel):
    username: str

class Register(BaseModel):
    username: str
    card_code: str

async def get_user(username):
    user = await db.users.find_one({"username": username})
    if not user:
        raise HTTPException(404, "User not found")
    return user

@app.post("/register")
async def register(u: User):
    if await db.users.find_one({"username": u.username}):
        raise HTTPException(400, "Username exists")
    u.password = bcrypt.hash(u.password)
    await db.users.insert_one({
        **u.dict(),
        "send_quota": 1, "receive_slots": 1,
        "send_count": 0, "receive_count": 0
    })
    return {"msg": "Registered"}

@app.post("/login")
async def login(l: Login):
    u = await db.users.find_one({"username": l.username})
    if not u or not bcrypt.verify(l.password, u["password"]):
        raise HTTPException(401, "Invalid credentials")
    return {"msg": f"Welcome {u['username']}"}

@app.post("/send")
async def send_postcard(d: Send):
    s = await get_user(d.username)
    if s["send_quota"] <= 0:
        raise HTTPException(400, "No send quota available")

    receivers = await db.users.find(
        {"username": {"$ne": d.username}, "receive_slots": {"$gt": 0}}
    ).to_list(None)
    if not receivers:
        raise HTTPException(400, "No receivers available")

    r = random.choice(receivers)
    code = f"PC-{ObjectId()}"

    await db.postcards.insert_one({
        "card_code": code,
        "sender_id": s["_id"],
        "receiver_id": r["_id"],
        "status": "assigned",
        "created_at": datetime.utcnow()
    })

    await db.users.update_one({"_id": s["_id"]}, {"$inc": {"send_quota": -1, "send_count": 1}})
    await db.users.update_one({"_id": r["_id"]}, {"$inc": {"receive_slots": -1}})

    return {"msg": "Send your postcard!", "card_code": code, "receiver": r["username"]}

@app.post("/register_card")
async def register_card(d: Register):
    r = await get_user(d.username)
    c = await db.postcards.find_one({"card_code": d.card_code})
    if not c: raise HTTPException(404, "Card not found")
    if c["receiver_id"] != r["_id"]: raise HTTPException(400, "Not your card")
    if c["status"] == "registered": raise HTTPException(400, "Already registered")

    await db.postcards.update_one({"_id": c["_id"]}, {"$set": {"status": "registered"}})
    await db.users.update_one({"_id": c["sender_id"]}, {"$inc": {"send_quota": 1}})
    await db.users.update_one({"_id": r["_id"]}, {"$inc": {"receive_count": 1, "receive_slots": 1}})

    return {"msg": "Card registered! Sender credited."}

@app.get("/stats/{username}")
async def stats(username: str):
    u = await get_user(username)
    return {
        "username": u["username"],
        "send_count": u["send_count"],
        "receive_count": u["receive_count"],
        "send_quota": u["send_quota"],
        "receive_slots": u["receive_slots"]
    }
