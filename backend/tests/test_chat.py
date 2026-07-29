import pytest
import unittest.mock as mock
from httpx import AsyncClient
from sqlalchemy.future import select
from app.db.models import User, DocumentMetadata, ChatSession, ChatMessage, RoleEnum
from app.core import security
from app.services.qdrant_service import QdrantService

@pytest.mark.asyncio
async def test_legal_chat_synthesis_loop(async_client: AsyncClient, user_token, db_session, regular_user):
    """
    Integration test verifying the end-to-end Legal RAG retrieval and synthesis loop:
    1. Indexes a mock legal clause directly in Qdrant.
    2. Opens a chat session via API.
    3. Mocks Gemini Embeddings and Chat response.
    4. Posts a message to the chat session.
    5. Asserts the response was synthesized using retrieved context and logged in Postgres.
    """
    # 1. Add DocumentMetadata
    doc_meta = DocumentMetadata(filename="merger_agreement.pdf", status="completed")
    db_session.add(doc_meta)
    await db_session.commit()
    await db_session.refresh(doc_meta)

    # 2. Seed Qdrant with a legal clause
    qdrant = QdrantService()
    collection_name = "legal_documents"
    
    mock_vector = [0.25] * 384
    clause_payload = {
        "document_id": doc_meta.id,
        "text": "Clause 8.3: Governing Law. This Agreement shall be governed by the laws of the State of Delaware.",
        "estimated_section": "Clause 8.3",
        "chunk_index": 0
    }
    
    await qdrant.upsert_points(
        collection_name=collection_name,
        points=[{
            "id": "11111111-2222-3333-4444-555555555555",
            "vector": mock_vector,
            "payload": clause_payload
        }]
    )

    # 3. Create Chat Session via API
    headers = {"Authorization": f"Bearer {user_token}"}
    session_res = await async_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Governing Law Consultation"},
        headers=headers
    )
    assert session_res.status_code == 200
    session_id = session_res.json()["id"]

    # 4. Mock Gemini Clients
    # Mock embedding query to return the vector matching Qdrant point
    mock_gemini_resp = "** Delaware State law governs the agreement ** (Ref: Clause 8.3)."
    
    with mock.patch("app.services.embedding.GeminiEmbeddingClient.get_embedding", return_value=mock_vector), \
         mock.patch("app.services.gemini_chat.GeminiChatClient.generate_response", return_value=mock_gemini_resp):
             
        # 5. Post message to API
        msg_res = await async_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages",
            json={"content": "What is the governing law of the merger?"},
            headers=headers
        )
        assert msg_res.status_code == 200
        msg_data = msg_res.json()
        assert msg_data["role"] == "model"
        assert "Delaware" in msg_data["content"]
        assert msg_data["confidence_level"] in ["High", "Medium", "Low"]
        assert len(msg_data["retrieved_context"]) > 0
        assert msg_data["retrieved_context"][0]["estimated_section"] == "Clause 8.3"
        assert "filename" in msg_data["retrieved_context"][0]
        assert "page_number" in msg_data["retrieved_context"][0]

        # 6. Verify Chat Log History in Postgres
        db_session.expire_all()
        result = await db_session.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id).order_by(ChatMessage.created_at.asc())
        )
        history = result.scalars().all()
        assert len(history) == 2  # User query + Assistant RAG answer
        assert history[0].role == "user"
        assert history[1].role == "model"
        assert history[1].confidence_level in ["High", "Medium", "Low"]
        assert history[1].retrieved_context[0]["estimated_section"] == "Clause 8.3"

    # Clean up Qdrant
    await qdrant.delete_collection(collection_name)

@pytest.mark.asyncio
async def test_legal_chat_streaming_loop(async_client: AsyncClient, user_token, db_session, regular_user):
    """
    Test verifying real-time SSE streaming chat endpoint /messages/stream.
    """
    headers = {"Authorization": f"Bearer {user_token}"}
    session_res = await async_client.post(
        "/api/v1/chat/sessions",
        json={"title": "Streaming Consultation"},
        headers=headers
    )
    assert session_res.status_code == 200
    session_id = session_res.json()["id"]

    async def mock_stream_gen(messages, system_instruction):
        yield "Delaware "
        yield "law."

    with mock.patch("app.services.embedding.GeminiEmbeddingClient.get_embedding", return_value=[0.1]*384), \
         mock.patch("app.services.gemini_chat.GeminiChatClient.generate_response_stream", side_effect=mock_stream_gen):
        
        msg_res = await async_client.post(
            f"/api/v1/chat/sessions/{session_id}/messages/stream",
            json={"content": "Streaming test prompt"},
            headers=headers
        )
        assert msg_res.status_code == 200
        assert "text/event-stream" in msg_res.headers["content-type"]
        body_text = msg_res.text
        assert "metadata" in body_text
        assert "chunk" in body_text
        assert "done" in body_text

