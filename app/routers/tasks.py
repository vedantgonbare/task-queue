from fastapi import APIRouter, Depends, HTTPException
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

@router.get("/", response_model=list[TaskResponse])
def get_all_tasks(db: Session = Depends(get_db)):
    return db.query(Task).order_by(Task.created_at.desc()).limit(50).all()

# NEW — modal calls this when a task row is clicked
@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task