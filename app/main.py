from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from contextlib import asynccontextmanager
from app.database import engine, Base
from app.routers import tasks
from app.websocket_manager import manager
from app.redis_subscriber import subscribe_to_updates
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import json

@asynccontextmanager
async def lifespan(app: FastAPI):
    task = asyncio.create_task(subscribe_to_updates())
    yield
    task.cancel()

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Queue API", lifespan=lifespan)

# ADD THIS — allows React on port 3000 to call FastAPI on port 8000
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
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