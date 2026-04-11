from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from uuid import UUID

class TaskCreate(BaseModel):
    payload: str

class TaskResponse(BaseModel):
    id:           UUID
    payload:      str
    status:       str
    created_at:   Optional[datetime] = None
    started_at:   Optional[datetime] = None   # NEW
    completed_at: Optional[datetime] = None   # NEW

    class Config:
        from_attributes = True