import os, io, zipfile, uvicorn, httpx, asyncio
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from fastapi import FastAPI, WebSocket, WebSocketDisconnect

app = FastAPI()

# Stream Config (Add these to Render Environment)
STREAM_API_KEY = os.environ.get("STREAM_API_KEY")
LIBRARY_ID = os.environ.get("LIBRARY_ID")

client = TelegramClient(StringSession(os.environ.get("SESSION_STRING")), 
                        int(os.environ.get("API_ID")), 
                        os.environ.get("API_HASH"))
active_connections = []

async def upload_to_stream(msg_id, filename):
    # 1. Create a video slot in Bunny Stream
    async with httpx.AsyncClient() as h_client:
        create_url = f"https://video.bunnycdn.com/library/{LIBRARY_ID}/videos"
        headers = {"AccessKey": STREAM_API_KEY, "accept": "application/json", "content-type": "application/json"}
        res = await h_client.post(create_url, headers=headers, json={"title": filename})
        video_id = res.json()["guid"]

        # 2. Pipe the extracted file data
        msg = await client.get_messages('me', ids=msg_id)
        async def stream_generator():
            full_zip = io.BytesIO()
            async for chunk in client.iter_download(msg.media): full_zip.write(chunk)
            full_zip.seek(0)
            with zipfile.ZipFile(full_zip) as z:
                with z.open(filename) as f:
                    while chunk := f.read(1024 * 1024): yield chunk

        upload_url = f"https://video.bunnycdn.com/library/{LIBRARY_ID}/videos/{video_id}"
        await h_client.put(upload_url, headers=headers, content=stream_generator())
        
        # 3. Send the Video ID to the website for embedding
        for ws in active_connections:
            await ws.send_json({"type": "STREAM_READY", "video_id": video_id, "library_id": LIBRARY_ID})

# ... WebSocket and client startup code same as before ...
