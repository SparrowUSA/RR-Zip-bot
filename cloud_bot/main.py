import os, io, zipfile, uvicorn, httpx, asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Render Environment Variables
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")
BUNNY_API_KEY = os.environ.get("BUNNY_API_KEY")
STORAGE_ZONE = os.environ.get("STORAGE_ZONE")
HOSTNAME = "storage.bunnycdn.com"

client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
active_connections = []

@client.on(events.NewMessage(chats='me'))
async def handle_new_zip(event):
    if event.file and event.file.ext == '.zip':
        # Download ZIP header to list files
        buffer = io.BytesIO()
        async for chunk in client.iter_download(event.media):
            buffer.write(chunk)
            if buffer.tell() > 1024 * 1024 * 10: break # Peek first 10MB
        
        buffer.seek(0)
        try:
            with zipfile.ZipFile(buffer) as z:
                videos = [f for f in z.namelist() if f.endswith(('.mp4', '.mkv', '.ts'))]
                for ws in active_connections:
                    await ws.send_json({"type": "LIST_FILES", "files": videos, "msg_id": event.id})
        except: pass

async def pipe_to_bunny(msg_id, filename):
    # 1. Get the original message
    msg = await client.get_messages('me', ids=msg_id)
    
    # 2. Extract and Stream
    async with httpx.AsyncClient(timeout=None) as h_client:
        async def stream_generator():
            full_zip = io.BytesIO()
            async for chunk in client.iter_download(msg.media):
                full_zip.write(chunk)
            
            full_zip.seek(0)
            with zipfile.ZipFile(full_zip) as z:
                with z.open(filename) as f:
                    while chunk := f.read(1024 * 1024): # 1MB chunks
                        yield chunk

        url = f"https://{HOSTNAME}/{STORAGE_ZONE}/{filename}"
        headers = {"AccessKey": BUNNY_API_KEY, "Content-Type": "application/octet-stream"}
        await h_client.put(url, content=stream_generator(), headers=headers)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            data = await websocket.receive_json()
            if data["type"] == "SELECT_FILE":
                await pipe_to_bunny(data["msg_id"], data["filename"])
    except WebSocketDisconnect:
        active_connections.remove(websocket)

@app.on_event("startup")
async def startup():
    await client.connect()
    asyncio.create_task(client.run_until_disconnected())

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
