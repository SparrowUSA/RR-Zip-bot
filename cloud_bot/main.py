import os
import gc
import uvicorn
from fastapi import FastAPI
from telethon import TelegramClient
from telethon.sessions import StringSession
from fastapi.middleware.cors import CORSMiddleware

# Initialize FastAPI
app = FastAPI()

# Enable CORS so your GitHub website can talk to this Render bot
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load variables from Render's Environment Settings
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

# Initialize Telegram Client
client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

@app.on_event("startup")
async def startup():
    await client.connect()
    print("✅ Bot connected to Telegram via Render")

@app.get("/")
async def root():
    return {"status": "Online", "platform": "Render", "memory_limit": "512MB"}

@app.get("/list/{msg_id}")
async def list_files(msg_id: int):
    try:
        # Aggressive memory cleanup for the 512MB limit
        gc.collect()
        
        msg = await client.get_messages('me', ids=msg_id)
        if not msg or not msg.media:
            return {"error": "No media found in this message ID"}
        
        return {
            "file_name": msg.file.name,
            "size_mb": round(msg.file.size / (1024 * 1024), 2)
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    # Render automatically assigns a PORT. We MUST use it.
    port = int(os.environ.get("PORT", 8080))
    # Use 1 worker to keep RAM usage as low as possible
    uvicorn.run(app, host="0.0.0.0", port=port, workers=1)
