import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

from app.db.models import DocumentMetadata
from app.services.parser import DocumentParser
from app.services.chunker import LegalChunker
from app.services.embedding import GeminiEmbeddingClient
from app.services.qdrant_service import QdrantService

class DocumentIngestionManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.emb_client = GeminiEmbeddingClient()
        self.qdrant_service = QdrantService()

    async def ingest_document(self, document_id: int, file_path: str) -> None:
        """
        Coordinates parsing, chunking, embedding, and vector index upserting.
        Updates DocumentMetadata status in DB.
        """
        # Fetch document metadata
        result = await self.db.execute(select(DocumentMetadata).where(DocumentMetadata.id == document_id))
        doc_meta = result.scalar_one_or_none()
        if not doc_meta:
            raise HTTPException(status_code=404, detail="Document metadata not found")

        try:
            # Step 1: Update status to processing
            doc_meta.status = "processing 0%"
            await self.db.commit()

            # Step 2: Parse File Pages
            pages = DocumentParser.parse_file_pages(file_path)
            if not pages or not any(p["text"].strip() for p in pages):
                raise ValueError("Parsed document is empty")

            # Step 3: Chunk Text with Page Tracking
            chunks = LegalChunker.split_pages(pages)

            # Step 4: Batch Embed Chunks (Gemini limits batch size to 100)
            chunk_texts = [c["text"] for c in chunks]
            batch_size = 50
            embeddings = []
            
            import asyncio
            for i in range(0, len(chunk_texts), batch_size):
                if i > 0:
                    await asyncio.sleep(1.0) # rate limit mitigation pacing
                batch_texts = chunk_texts[i:i + batch_size]
                batch_embeddings = await self.emb_client.get_embeddings_batch(batch_texts)
                embeddings.extend(batch_embeddings)
                
                progress = int((len(embeddings) / len(chunk_texts)) * 100)
                doc_meta.status = f"processing {progress}%"
                await self.db.commit()

            # Step 5: Prepare Qdrant Points
            collection_name = "legal_documents"
            doc_meta.qdrant_collection_name = collection_name
            
            points = []
            for idx, chunk in enumerate(chunks):
                points.append({
                    "id": str(uuid.uuid4()),
                    "vector": embeddings[idx],
                    "payload": {
                        "document_id": doc_meta.id,
                        "filename": doc_meta.filename,
                        "text": chunk["text"],
                        "estimated_section": chunk["metadata"]["estimated_section"],
                        "page_number": chunk["metadata"].get("page_number", 1),
                        "chunk_index": chunk["metadata"]["chunk_index"]
                    }
                })

            # Step 6: Upsert to Qdrant
            await self.qdrant_service.upsert_points(collection_name, points)

            # Step 7: Update DB Status to Completed
            doc_meta.status = "completed"
            await self.db.commit()

        except Exception as e:
            # Handle failure
            doc_meta.status = "failed"
            await self.db.commit()
            raise HTTPException(status_code=500, detail=f"Ingestion pipeline failed: {str(e)}")
