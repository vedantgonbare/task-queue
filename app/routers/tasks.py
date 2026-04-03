from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db, redis_client
from app.models import Task
from app.schemas import TaskCreate, TaskResponse
import uuid

router = APIRouter()

@router.post("/", response_model=TaskResponse)
def create_task(task: TaskCreate, db: Session = Depends(get_db)):
    # 1. Create task in PostgreSQL
    db_task = Task(
        id=uuid.uuid4(),
        payload=task.payload,
        status="pending"
    )
    db.add(db_task)
    db.commit()
    db.refresh(db_task)

    # 2. Push task ID to Redis queue
    redis_client.rpush("task_queue", str(db_task.id))

    return db_task

@router.get("/{task_id}", response_model=TaskResponse)
def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task