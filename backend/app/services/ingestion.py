import uuid
import json
import re
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

from app.db.models import DocumentMetadata
from app.services.parser import DocumentParser
from app.services.chunker import LegalChunker
from app.services.embedding import GeminiEmbeddingClient
from app.services.qdrant_service import QdrantService
from app.services.gemini_chat import GeminiChatClient

class DocumentIngestionManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.emb_client = GeminiEmbeddingClient()
        self.qdrant_service = QdrantService()
        self.chat_client = GeminiChatClient()

    async def _extract_metadata_from_pages(self, pages: list, filename: str) -> dict:
        """
        Uses an LLM to read the beginning of the document and extract metadata 
        (e.g., case_name, date, court, statute_reference).
        """
        # Grab first ~3000 characters from the first few pages
        context_text = ""
        for p in pages[:3]:
            context_text += p.get("text", "") + "\n"
            if len(context_text) > 3000:
                context_text = context_text[:3000]
                break

        if not context_text.strip():
            return {}

        prompt = f"""
        You are a legal metadata extractor. Read the following text from the beginning of a legal document (filename: {filename}).
        Extract the following fields if present:
        - case_name
        - date (year or full date)
        - court
        - statute_reference (e.g. IPC, CrPC, specific acts mentioned)

        If a field is not found, leave it empty.
        Return ONLY a raw JSON object containing these keys. No markdown blocks, no other text.
        
        Text:
        {context_text}
        """
        try:
            response = await self.chat_client.generate_response(
                messages=[{"role": "user", "content": prompt}],
                system_instruction="You output raw JSON only."
            )
            # Try to parse json, remove markdown block if present
            clean_json = re.sub(r'```(?:json)?\s*([\s\S]*?)\s*```', r'\1', response.strip())
            metadata = json.loads(clean_json)
            # Ensure it's a dict
            if isinstance(metadata, dict):
                # Clean up empty values
                return {k: str(v) for k, v in metadata.items() if v}
        except Exception as e:
            print(f"Failed to extract metadata: {e}")
        
        return {}

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
            pages = await DocumentParser.parse_file_pages(file_path)
            if not pages or not any(p["text"].strip() for p in pages):
                raise ValueError("Parsed document is empty")

            # Step 2.5: Extract Global Metadata
            global_metadata = await self._extract_metadata_from_pages(pages, doc_meta.filename)
            
            if doc_meta.workspace:
                global_metadata["workspace"] = doc_meta.workspace
            if doc_meta.document_type:
                global_metadata["document_type"] = doc_meta.document_type
            if doc_meta.industry:
                global_metadata["industry"] = doc_meta.industry
            if doc_meta.jurisdiction:
                global_metadata["jurisdiction"] = doc_meta.jurisdiction
            if doc_meta.state:
                global_metadata["state"] = doc_meta.state

            # Step 3: Chunk Text with Page Tracking and Metadata
            chunks = LegalChunker.split_pages(pages, global_metadata=global_metadata)

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
                payload = {
                    "document_id": doc_meta.id,
                    "filename": doc_meta.filename,
                    "text": chunk["text"],
                }
                # Add all extracted and chunk-specific metadata
                payload.update(chunk["metadata"])
                
                points.append({
                    "id": str(uuid.uuid4()),
                    "vector": embeddings[idx],
                    "payload": payload
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
