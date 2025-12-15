from pydantic import BaseModel
from typing import Optional, Union
from datetime import datetime

class UserBase(BaseModel):
    email: str

class UserCreate(UserBase):
    password: str
    name: str

class User(UserBase):
    id: str
    name: str
    created_at: Optional[datetime] = None

    class Config:
        orm_mode = True

class UserLogin(BaseModel):
    email: str
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

class ChatMessage(BaseModel):
    content: str
    sender: str  # "user" or "assistant"
    timestamp: Optional[datetime] = None