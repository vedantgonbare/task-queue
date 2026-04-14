import asyncio
import json
import redis
import os
from app.websocket_manager import manager

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

async def subscribe_to_updates():
    """Listen to Redis channel and broadcast to WebSocket clients"""
    r = redis.from_url(REDIS_URL)
    pubsub = r.pubsub()
    pubsub.subscribe("task_updates")
    print("[Redis Subscriber] Listening for task updates...")

    while True:
        message = pubsub.get_message()
        if message and message["type"] == "message":
            data = json.loads(message["data"])
            await manager.broadcast(data)
        await asyncio.sleep(0.01)  # 10ms polling