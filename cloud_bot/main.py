import os
import gc
import uvicorn
from fastapi import FastAPI
from telethon import TelegramClient
from telethon.sessions import StringSession
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

app = FastAPI()

# Allows your GitHub website to talk to this Northflank bot
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

API_ID = int(os.getenv("API_ID", 0))
API_HASH = os.getenv("API_HASH", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@app.on_event("startup")
async def startup():
    await client.connect()
    print("✅ Bot Connected to Telegram")

@app.get("/")
async def health_check():
    return {"status": "running", "host": "northflank"}

@app.get("/list/{msg_id}")
async def list_files(msg_id: int):
    try:
        # Optimized memory cleanup before heavy task
        gc.collect()
        msg = await client.get_messages('me', ids=msg_id)
        if not msg or not msg.media:
            return {"error": "No media found"}
        
        # Simplified for testing; adds Bunny.net logic here later
        return {"file": msg.file.name, "size": msg.file.size}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
