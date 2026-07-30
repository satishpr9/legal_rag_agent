import asyncio
from typing import List
from sentence_transformers import SentenceTransformer

class GeminiEmbeddingClient:
    def __init__(self):
        # We load the lightweight, fast open-source model locally
        self.model_name = "all-MiniLM-L6-v2"
        try:
            self.model = SentenceTransformer(self.model_name, local_files_only=True)
        except Exception:
            self.model = SentenceTransformer(self.model_name)
        
    async def get_embedding(self, text: str) -> List[float]:
        """
        Generates embedding for a single string.
        """
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None, lambda: self.model.encode(text, convert_to_numpy=True).tolist()
        )
        return embedding

    async def get_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generates embeddings for a batch of strings.
        """
        if not texts:
            return []
            
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(
            None, lambda: self.model.encode(texts, convert_to_numpy=True).tolist()
        )
        return embeddings
