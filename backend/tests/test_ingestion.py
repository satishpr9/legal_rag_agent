import pytest
import os
import unittest.mock as mock
from httpx import AsyncClient
from sqlalchemy.future import select
from app.db.models import User, DocumentMetadata, RoleEnum
from app.core import security
from app.services.qdrant_service import QdrantService
from app.services.ingestion import DocumentIngestionManager

@pytest.mark.asyncio
async def test_document_ingestion_pipeline_direct(db_session, admin_user):
    """
    Test the DocumentIngestionManager logic directly (synchronous flow).
    This avoids event loop conflicts from background tasks during testing.
    """
    # 1. Create DocumentMetadata directly in DB
    doc_meta = DocumentMetadata(filename="test_doc.txt", status="pending")
    db_session.add(doc_meta)
    await db_session.commit()
    await db_session.refresh(doc_meta)

    # 2. Write a mock TXT document locally
    test_doc_path = "tests/test_doc.txt"
    test_doc_content = "Article 1. The contract is binding. Section 2. Either party can terminate with 30 days notice."
    os.makedirs(os.path.dirname(test_doc_path), exist_ok=True)
    with open(test_doc_path, "w", encoding="utf-8") as f:
        f.write(test_doc_content)

    # 3. Mock the Gemini Embedding Client
    mock_embedding = [0.1] * 384
    with mock.patch("app.services.embedding.GeminiEmbeddingClient.get_embeddings_batch", return_value=[mock_embedding, mock_embedding]):
        # Run Ingestion directly
        ingestion_manager = DocumentIngestionManager(db_session)
        await ingestion_manager.ingest_document(doc_meta.id, test_doc_path)

        # 4. Verify Ingestion Success in Postgres DB
        await db_session.refresh(doc_meta)
        assert doc_meta.status == "completed"

        # 5. Verify Qdrant vectors
        qdrant = QdrantService()
        collection_name = "legal_documents"
        
        # Test collection existence
        exists = await qdrant.collection_exists(collection_name)
        assert exists is True

        # Test searching the document point in Qdrant
        search_results = await qdrant.search_points(
            collection_name=collection_name,
            query_vector=mock_embedding,
            limit=2
        )
        assert len(search_results) > 0
        assert search_results[0]["payload"]["document_id"] == doc_meta.id
        assert "binding" in search_results[0]["payload"]["text"]

        # Clean up Qdrant collection
        await qdrant.delete_collection(collection_name)

    # Clean up file
    if os.path.exists(test_doc_path):
        os.remove(test_doc_path)

@pytest.mark.asyncio
async def test_document_ingestion_api_endpoint(async_client: AsyncClient, admin_token, db_session, admin_user):
    """
    Test the ingestion API route triggers background task execution correctly.
    """
    ws_headers = {"Authorization": f"Bearer {admin_token}"}
    with mock.patch("app.services.ingestion.DocumentIngestionManager.ingest_document") as mock_ingest:
        ingest_response = await async_client.post(
            "/api/v1/admin/documents/ingest",
            json={
                "filename": "test_doc.txt",
                "file_path": "tests/test_doc.txt"
            },
            headers=ws_headers
        )
        assert ingest_response.status_code == 200
        assert ingest_response.json()["status"] in ["pending", "processing 0%"]
        
        # Verify background task was scheduled
        mock_ingest.assert_called_once()

@pytest.mark.asyncio
async def test_document_upload_api_endpoint(async_client: AsyncClient, admin_token, db_session, admin_user):
    """
    Test that the document upload multipart API route accepts file uploads and schedules ingestion.
    """
    # Trigger Upload via API
    ws_headers = {"Authorization": f"Bearer {admin_token}"}
    mock_file_content = b"Article 1. Acme corp buys Beta Inc."
    files = {"file": ("merger.txt", mock_file_content, "text/plain")}

    with mock.patch("app.services.ingestion.DocumentIngestionManager.ingest_document") as mock_ingest:
        upload_response = await async_client.post(
            "/api/v1/admin/documents/upload",
            files=files,
            headers=ws_headers
        )
        assert upload_response.status_code == 200
        assert upload_response.json()["filename"] == "merger.txt"
        assert upload_response.json()["status"] in ["pending", "processing 0%"]

        # Verify background task was scheduled
        mock_ingest.assert_called_once()
        
        # Clean up uploaded file if it was saved
        saved_file = "uploads/merger.txt"
        if os.path.exists(saved_file):
            os.remove(saved_file)
