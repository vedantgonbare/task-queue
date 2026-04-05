import asyncio
import json
from app.database import redis_client
from app.websocket_manager import manager

async def subscribe_to_updates():
    """Listen to Redis channel and broadcast to WebSocket clients"""
    pubsub = redis_client.pubsub()
    pubsub.subscribe("task_updates")
    print("[Redis Subscriber] Listening for task updates...")

    while True:
        message = pubsub.get_message()
        if message and message["type"] == "message":
            data = json.loads(message["data"])
            await manager.broadcast(data)
        await asyncio.sleep(0.01)  # 10ms polling