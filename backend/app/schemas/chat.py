from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatMessageCreate(BaseModel):
    content: str

class ChatMessageResponse(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    retrieved_context: Optional[list[dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True
