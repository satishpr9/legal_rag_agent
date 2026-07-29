from qdrant_client import AsyncQdrantClient
from pydantic_settings import BaseSettings

class QdrantSettings(BaseSettings):
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    
qdrant_settings = QdrantSettings()

async def get_qdrant_client() -> AsyncQdrantClient:
    return AsyncQdrantClient(host=qdrant_settings.QDRANT_HOST, port=qdrant_settings.QDRANT_PORT)
