from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class LoggerBase(BaseModel):
    action: str
    created_at: Optional[datetime] = None


class LoggerCreate(LoggerBase):
    pass


class LoggerUpdate(LoggerBase):
    action: Optional[str]
    created_at: Optional[datetime]


class LoggerResponse(LoggerBase):
    id: str
    user_id: str

    class Config:
        orm_mode = True