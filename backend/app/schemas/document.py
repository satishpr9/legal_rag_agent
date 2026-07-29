from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class DocumentMetadataBase(BaseModel):
    filename: str

class DocumentIngestRequest(DocumentMetadataBase):
    file_path: str

class DocumentMetadataResponse(DocumentMetadataBase):
    id: int
    qdrant_collection_name: Optional[str] = None
    status: str
    created_at: datetime

    class Config:
        from_attributes = True
