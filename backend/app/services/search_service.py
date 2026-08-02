from typing import List, Dict, Any
from app.services.embedding import GeminiEmbeddingClient
from app.services.qdrant_service import QdrantService
from app.core.config import settings
from rank_bm25 import BM25Okapi
import re

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
        
    def _tokenize(self, text: str) -> List[str]:
        # Simple word tokenization for BM25
        text = text.lower()
        return [word for word in re.split(r'\W+', text) if word]
        
    def expand_query(self, query: str) -> str:
        """
        Expands legal acronyms in the query to improve both vector search and keyword matching.
        Returns expanded_query_string.
        """
        raw_words = query.lower().split()
        
        expanded_phrases = []
        for word in raw_words:
            clean_word = "".join(c for c in word if c.isalnum())
            if clean_word in LEGAL_ACRONYMS:
                expanded_phrases.append(LEGAL_ACRONYMS[clean_word])
                
        if expanded_phrases:
            search_query = f"{query} {' '.join(expanded_phrases)}"
        else:
            search_query = query
            
        return search_query

    async def _fetch_parent_context(
        self, leaf_results: List[Dict[str, Any]]
    ) -> Dict[str, str]:
        """
        For leaf nodes that have a parent_node_id, fetches the parent node's text
        from Qdrant to provide broader context to the LLM.
        Returns a mapping of parent_node_id -> parent_text.
        """
        parent_ids = set()
        for result in leaf_results:
            parent_id = result.get("parent_node_id")
            if parent_id:
                parent_ids.add(parent_id)

        if not parent_ids:
            return {}

        parent_texts = {}
        collection_name = settings.QDRANT_COLLECTION

        for parent_id in parent_ids:
            # Search for the parent node by its node_id in payload
            qdrant_filter = {
                "must": [
                    {"key": "node_id", "match": {"value": parent_id}},
                    {"key": "node_type", "match": {"value": "parent"}}
                ]
            }
            # Use a zero vector since we're filtering by ID, not by similarity
            zero_vector = [0.0] * settings.EMBEDDING_DIMENSION
            results = await self.qdrant_service.search_points(
                collection_name=collection_name,
                query_vector=zero_vector,
                limit=1,
                qdrant_filter=qdrant_filter
            )
            if results:
                payload = results[0].get("payload", {})
                parent_texts[parent_id] = payload.get("text", "")

        return parent_texts

    async def retrieve_context(
        self, 
        query: str, 
        limit: int = 5,
        filters: dict = None
    ) -> List[Dict[str, Any]]:
        """
        Hybrid retrieval with hierarchical parent context:
        1. Expand acronyms and embed query
        2. Over-fetch leaf candidates via dense vector search
        3. Re-rank with BM25 sparse matching
        4. Fetch parent context for top results (small-to-big retrieval)
        """
        # Step 1: Expand acronyms and embed search query
        search_query = self.expand_query(query)
        query_vector = await self.embedding_client.get_embedding(search_query)
        
        # Step 2: Over-fetch leaf candidates using Vector Search
        # Only search leaf nodes (which have real embeddings)
        collection_name = settings.QDRANT_COLLECTION
        candidate_limit = max(limit * 15, 50)
        
        # Build filter: always filter for leaf nodes, plus any user-supplied filters
        must_clauses = [
            {"key": "node_type", "match": {"value": "leaf"}}
        ]
        if filters:
            for k, v in filters.items():
                if isinstance(v, list) and v:
                    must_clauses.append({"key": k, "match": {"any": v}})
                elif v:
                    must_clauses.append({"key": k, "match": {"value": v}})
        
        qdrant_filter = {"must": must_clauses}
                
        search_results = await self.qdrant_service.search_points(
            collection_name=collection_name,
            query_vector=query_vector,
            limit=candidate_limit,
            qdrant_filter=qdrant_filter
        )
        
        if not search_results:
            return []
            
        # Step 3: Prepare BM25 local corpus
        tokenized_corpus = []
        parsed_results = []
        
        for point in search_results:
            payload = point.get("payload", {})
            semantic_score = point.get("score", 0.0)
            
            # Text to run BM25 against
            # Use section header info from metadata if available
            header = payload.get("estimated_section", "") or payload.get("source_file", "")
            content = payload.get("text", "")
            bm25_text = f"{header} {header} {content}"
            tokenized_corpus.append(self._tokenize(bm25_text))
            
            doc_id = payload.get("document_id")
            filename = payload.get("filename") or (f"Document #{doc_id}" if doc_id else "Legal Document")
            
            parsed_results.append({
                "text": content,
                "semantic_score": semantic_score,
                "document_id": doc_id,
                "filename": filename,
                "estimated_section": header or "General",
                "page_number": payload.get("page_number", 1),
                "chunk_index": payload.get("chunk_index"),
                "node_id": payload.get("node_id"),
                "parent_node_id": payload.get("parent_node_id"),
            })
            
        # Step 4: Calculate BM25 scores
        bm25 = BM25Okapi(tokenized_corpus)
        tokenized_query = self._tokenize(search_query)
        bm25_scores = bm25.get_scores(tokenized_query)
        
        # Normalize scores to 0-1 range for fair combination
        max_bm25 = max(bm25_scores) if len(bm25_scores) > 0 and max(bm25_scores) > 0 else 1.0
        max_semantic = max(r["semantic_score"] for r in parsed_results) if parsed_results else 1.0
        
        for i, res in enumerate(parsed_results):
            norm_bm25 = bm25_scores[i] / max_bm25
            norm_semantic = res["semantic_score"] / max_semantic
            # Hybrid Score formula: 70% Semantic, 30% BM25
            res["score"] = (0.7 * norm_semantic) + (0.3 * norm_bm25)
            
        # Step 5: Sort by hybrid score descending and slice to limit
        parsed_results.sort(key=lambda x: x["score"], reverse=True)
        top_results = parsed_results[:limit]

        # Step 6: Fetch parent context for top results (small-to-big retrieval)
        parent_texts = await self._fetch_parent_context(top_results)

        # Enrich results with parent context
        for result in top_results:
            parent_id = result.get("parent_node_id")
            if parent_id and parent_id in parent_texts:
                result["parent_context"] = parent_texts[parent_id]

        return top_results
