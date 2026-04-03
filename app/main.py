from fastapi import FastAPI
from app.database import engine, Base
from app.routers import tasks

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Task Queue API")

app.include_router(tasks.router, prefix="/tasks", tags=["tasks"])

@app.get("/")
def root():
    return {"message": "Task Queue API is running"}