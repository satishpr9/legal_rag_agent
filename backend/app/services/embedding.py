import asyncio
from typing import List

from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from app.core.config import settings

_GLOBAL_EMBED_MODEL = None

class GeminiEmbeddingClient:
    def __init__(self):
        self.model_name = settings.EMBEDDING_MODEL

    def _get_model(self) -> HuggingFaceEmbedding:
        global _GLOBAL_EMBED_MODEL
        if _GLOBAL_EMBED_MODEL is None:
            _GLOBAL_EMBED_MODEL = HuggingFaceEmbedding(
                model_name=self.model_name,
                trust_remote_code=True,
            )
        return _GLOBAL_EMBED_MODEL

    def get_llama_index_embedding(self) -> HuggingFaceEmbedding:
        return self._get_model()

    async def get_embedding(self, text: str) -> List[float]:
        return await asyncio.get_running_loop().run_in_executor(
            None, lambda: self._get_model()._get_text_embedding(text)
        )

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        return await asyncio.get_running_loop().run_in_executor(
            None, lambda: self._get_model()._get_text_embeddings(texts)
        )
