from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import tasks
from app.websocket_manager import manager
from app.redis_subscriber import subscribe_to_updates
import asyncio
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Start Redis subscriber as background task when app starts
    task = asyncio.create_task(subscribe_to_updates())
    yield
    # Cancel when app shuts down
    task.cancel()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Queue API", lifespan=lifespan)

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

@app.get("/")
def root():
    return {"message": "Task Queue API is running"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(json.dumps({"type": "pong"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)