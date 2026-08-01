from pydantic import BaseModel
from typing import Optional, Any
from datetime import datetime

class ChatSessionCreate(BaseModel):
    title: Optional[str] = "New Chat"
    filters: Optional[dict] = None

class ChatSessionResponse(BaseModel):
    id: int
    title: str
    filters: Optional[dict] = None
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
    confidence_level: Optional[str] = "Medium"
    disclaimer: Optional[str] = "Disclaimer: Response is for informational and legal research purposes only and does not constitute formal legal advice."
    retrieved_context: Optional[list[dict[str, Any]]] = None
    created_at: datetime

    class Config:
        from_attributes = True
