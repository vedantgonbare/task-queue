from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import Task
from app.schemas import TaskCreate, TaskResponse
import json
import redis

router = APIRouter()

r = redis.Redis(host='localhost', port=6379, db=0)

@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    db_task = Task(payload=task.payload, status="pending")
    db.add(db_task)
    db.commit()
    db.refresh(db_task)
    r.rpush("task_queue", json.dumps({"id": db_task.id, "payload": db_task.payload}))
    return db_task

# ADD THIS — React will call this on load to get existing tasks
@router.get("/", response_model=list[TaskResponse])
def get_all_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).limit(50).all()