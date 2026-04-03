from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from typing import Optional

class TaskCreate(BaseModel):
    payload: str

class TaskResponse(BaseModel):
    id: UUID
    status: str
    payload: str
    result: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True