from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import tasks
from app.websocket_manager import manager
from app.redis_subscriber import subscribe_to_updates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json
import redis
import os
import time
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import Task

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")

# ── Inline Worker ──────────────────────────────────────────────
def process_task(task_data: dict):
    db: Session = SessionLocal()
    r = redis.from_url(REDIS_URL)
    try:
        task = db.query(Task).filter(Task.id == task_data["id"]).first()
        if not task:
            return

        task.status     = "running"
        task.started_at = datetime.now(timezone.utc)
        db.commit()

        r.publish("task_updates", json.dumps({
            "task_id": str(task.id),
            "status":  "running",
            "payload": task.payload,
        }))
        print(f"[Worker] {str(task.id)[:8]} Running…")

        time.sleep(2)

        task.status       = "done"
        task.completed_at = datetime.now(timezone.utc)
        db.commit()

        r.publish("task_updates", json.dumps({
            "task_id": str(task.id),
            "status":  "done",
            "payload": task.payload,
        }))
        print(f"[Worker] {str(task.id)[:8]} Done ✓")

    except Exception as e:
        if task:
            task.status       = "failed"
            task.completed_at = datetime.now(timezone.utc)
            db.commit()
            r.publish("task_updates", json.dumps({
                "task_id": str(task.id),
                "status":  "failed",
            }))
        print(f"[Worker] Error: {e}")
    finally:
        db.close()

async def worker_loop():
    r = redis.from_url(REDIS_URL)
    print("[Worker] Started inside FastAPI…")
    loop = asyncio.get_event_loop()
    while True:
        try:
            result = await loop.run_in_executor(
                None, lambda: r.blpop("task_queue", timeout=1)
            )
            if result:
                _, raw = result
                task_data = json.loads(raw)
                print(f"[Worker] Picked up {task_data['id'][:8]}…")
                await loop.run_in_executor(None, process_task, task_data)
        except Exception as e:
            print(f"[Worker Loop] Error: {e}")
            await asyncio.sleep(1)

@asynccontextmanager
async def lifespan(app: FastAPI):
    redis_task  = asyncio.create_task(subscribe_to_updates())
    worker_task = asyncio.create_task(worker_loop())
    yield
    redis_task.cancel()
    worker_task.cancel()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Queue API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)