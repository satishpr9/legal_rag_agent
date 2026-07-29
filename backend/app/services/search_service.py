from typing import List, Dict, Any
from app.services.embedding import GeminiEmbeddingClient
from app.services.qdrant_service import QdrantService

LEGAL_ACRONYMS = {
    "bns": "Bharatiya Nyaya Sanhita",
    "bnss": "Bharatiya Nagarik Suraksha Sanhita",
    "bsa": "Bharatiya Sakshya Adhiniyam",
    "ipc": "Indian Penal Code",
    "crpc": "Code of Criminal Procedure",
    "cpc": "Code of Civil Procedure",
    "dpdp": "Digital Personal Data Protection",
    "dpdpa": "Digital Personal Data Protection Act",
    "ibc": "Insolvency and Bankruptcy Code",
    "nclt": "National Company Law Tribunal",
    "nclat": "National Company Law Appellate Tribunal",
    "sebi": "Securities and Exchange Board of India",
    "rbi": "Reserve Bank of India",
    "llp": "Limited Liability Partnership",
    "cpa": "Consumer Protection Act",
    "pocso": "Protection of Children from Sexual Offences",
    "posh": "Sexual Harassment of Women at Workplace",
    "fir": "First Information Report",
    "pil": "Public Interest Litigation",
    "rti": "Right to Information",
}

class LegalRetrievalService:
    def __init__(self):
        self.embedding_client = GeminiEmbeddingClient()
        self.qdrant_service = QdrantService()
        
    def expand_query(self, query: str) -> tuple[str, set[str]]:
        """
        Expands legal acronyms in the query to improve both vector search and keyword matching.
        Returns (expanded_query_string, set_of_query_keywords).
        """
        raw_words = query.lower().split()
        stop_words = {"what", "is", "the", "of", "in", "to", "for", "with", "on", "at", "by", "an", "a", "this", "that", "and", "or"}
        
        expanded_phrases = []
        for word in raw_words:
            clean_word = "".join(c for c in word if c.isalnum())
            if clean_word in LEGAL_ACRONYMS:
                expanded_phrases.append(LEGAL_ACRONYMS[clean_word])
                
        if expanded_phrases:
            search_query = f"{query} ({' '.join(expanded_phrases)})"
        else:
            search_query = query

        # Extract keywords from both raw and expanded query
        all_words = search_query.lower().split()
        query_keywords = {
            "".join(c for c in w if c.isalnum())
            for w in all_words
            if "".join(c for c in w if c.isalnum()) and "".join(c for c in w if c.isalnum()) not in stop_words
        }
        
        return search_query, query_keywords

    async def retrieve_context(
        self, 
        query: str, 
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Embeds the query (with acronym expansion) and searches Qdrant for relevant legal contexts.
        Uses Hybrid Search logic: over-fetches candidates via vector search and re-ranks them based
        on keyword overlap to prioritize exact matches for section headers and legal terms.
        """
        # Step 1: Expand acronyms and embed search query
        search_query, query_keywords = self.expand_query(query)
        query_vector = await self.embedding_client.get_embedding(search_query)
        
        # Step 2: Over-fetch candidates using Vector Search (fetch 3x of limit, minimum 15)
        collection_name = "legal_documents"
        candidate_limit = max(limit * 3, 15)
        search_results = await self.qdrant_service.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=candidate_limit
        )
        
        # Step 3: Parse and compute local keyword re-scoring
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
            
            doc_id = payload.get("document_id")
            filename = payload.get("filename") or (f"Document #{doc_id}" if doc_id else "Legal Document")
            page_number = payload.get("page_number", 1)

            retrieved_contexts.append({
                "text": payload.get("text", ""),
                "score": hybrid_score,
                "document_id": doc_id,
                "filename": filename,
                "estimated_section": payload.get("estimated_section", "General"),
                "page_number": page_number,
                "chunk_index": payload.get("chunk_index")
            })
            
        # Step 4: Re-rank by hybrid score descending and slice to limit
        retrieved_contexts.sort(key=lambda x: x["score"], reverse=True)
        return retrieved_contexts[:limit]

