from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

class LoginRequest(BaseModel):
    email: str
    password: str

class AccessToken(BaseModel):
    access_token: str
    token_type: str


class UserBase(BaseModel):
    name_complete: str
    role: str
    active: bool = False


class UserCreate(UserBase):
    email: EmailStr
    password: str


class UserUpdate(UserBase):
    name_complete: Optional[str]
    email: Optional[EmailStr]
    role: Optional[str]


class UserResponse(UserBase):
    id: str
    email: EmailStr
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True