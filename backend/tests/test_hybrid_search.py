import pytest
from app.db.models import DocumentMetadata
from app.services.qdrant_service import QdrantService
from app.services.search_service import LegalRetrievalService
import unittest.mock as mock

@pytest.mark.asyncio
async def test_hybrid_search_rescoring_ranking(db_session, admin_user):
    """
    Verifies that the hybrid search re-scorer correctly ranks documents matching
    both semantic concepts and exact keywords/section headers higher than
    documents with identical semantic embeddings but mismatched keywords.
    """
    # 1. Create Document
    doc = DocumentMetadata(filename="sample_contract.pdf", status="completed")
    db_session.add(doc)
    await db_session.commit()
    await db_session.refresh(doc)
    
    # 2. Seed Qdrant with two points having the EXACT same vector (so semantic score is identical)
    # but different text contents and estimated section headers
    qdrant = QdrantService()
    collection_name = "legal_documents"
    
    shared_vector = [0.15] * 384
    
    points = [
        {
            "id": "22222222-1111-3333-4444-555555555555",
            "vector": shared_vector,
            "payload": {
                "document_id": doc.id,
                "text": "This agreement shall be governed by the laws of New York.",
                "estimated_section": "Clause 9.1: Law",
                "chunk_index": 0
            }
        },
        {
            "id": "33333333-1111-3333-4444-555555555555",
            "vector": shared_vector,
            "payload": {
                "document_id": doc.id,
                "text": "This agreement shall be governed by the laws of New York.",
                "estimated_section": "Clause 8.3: Governing Law", # Match on 8.3 and Governing Law
                "chunk_index": 1
            }
        }
    ]
    
    await qdrant.upsert_points(collection_name=collection_name, points=points)
    
    # 3. Retrieve context with a keyword-specific query
    # The query mentions "Clause 8.3" and "Governing Law"
    retrieval_service = LegalRetrievalService()
    
    with mock.patch("app.services.embedding.GeminiEmbeddingClient.get_embedding", return_value=shared_vector):
        results = await retrieval_service.retrieve_context(
            query="What is the Governing Law under Clause 8.3?",
            limit=2
        )
        
        # 4. Assert that Clause 8.3 is ranked FIRST due to keyword match bonus,
        # despite having the exact same semantic vector and vector similarity score
        assert len(results) == 2
        assert results[0]["estimated_section"] == "Clause 8.3: Governing Law"
        assert results[1]["estimated_section"] == "Clause 9.1: Law"
        assert results[0]["score"] > results[1]["score"]
        
    # Clean up Qdrant
    await qdrant.delete_collection(collection_name)
