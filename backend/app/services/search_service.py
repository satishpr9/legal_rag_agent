from typing import List, Dict, Any
from app.services.embedding import GeminiEmbeddingClient
from app.services.qdrant_service import QdrantService

class LegalRetrievalService:
    def __init__(self):
        self.embedding_client = GeminiEmbeddingClient()
        self.qdrant_service = QdrantService()
        
    async def retrieve_context(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Embeds the query and searches Qdrant for relevant legal contexts in the global collection.
        Uses Hybrid Search logic: over-fetches candidates via vector search and re-ranks them based
        on keyword overlap to prioritize exact matches for section headers and legal terms.
        """
        # Step 1: Embed query
        query_vector = await self.embedding_client.get_embedding(query)
        
        # Step 2: Over-fetch candidates using Vector Search (fetch 3x of limit, minimum 15)
        collection_name = "legal_documents"
        candidate_limit = max(limit * 3, 15)
        search_results = await self.qdrant_service.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=candidate_limit
        )
        
        # Step 3: Parse and compute local keyword re-scoring
        query_words = set(query.lower().split())
        # Filter out minor helper words to prevent false boosts on stop words
        stop_words = {"what", "is", "the", "of", "in", "to", "for", "with", "on", "at", "by", "an", "a", "this", "that", "and", "or"}
        query_keywords = {word for word in query_words if word.isalnum() and word not in stop_words}
        
        retrieved_contexts = []
        for point in search_results:
            payload = point.get("payload", {})
            text_content = payload.get("text", "").lower()
            estimated_section = payload.get("estimated_section", "").lower()
            
            # Compute term match ratio
            match_count = 0
            if query_keywords:
                for keyword in query_keywords:
                    # Grant higher weight if match is found in the estimated section header itself
                    if keyword in estimated_section:
                        match_count += 1.5
                    elif keyword in text_content:
                        match_count += 1.0
                match_ratio = match_count / len(query_keywords)
            else:
                match_ratio = 0.0
                
            # Hybrid Score = Semantic Vector Score + 0.3 * Keyword Match Ratio
            semantic_score = point.get("score", 0.0)
            hybrid_score = semantic_score + (0.3 * match_ratio)
            
            retrieved_contexts.append({
                "text": payload.get("text", ""),
                "score": hybrid_score,
                "document_id": payload.get("document_id"),
                "estimated_section": payload.get("estimated_section", "General"),
                "chunk_index": payload.get("chunk_index")
            })
            
        # Step 4: Re-rank by hybrid score descending and slice to limit
        retrieved_contexts.sort(key=lambda x: x["score"], reverse=True)
        return retrieved_contexts[:limit]

