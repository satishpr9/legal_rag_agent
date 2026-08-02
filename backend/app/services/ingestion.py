import uuid
import json
import re
import asyncio
from typing import List, Dict, Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException

from llama_index.core.schema import TextNode
from llama_index.core.ingestion import IngestionPipeline

from app.db.models import DocumentMetadata
from app.services.parser import DocumentParser
from app.services.chunker import LegalHierarchicalChunker
from app.services.embedding import GeminiEmbeddingClient
from app.services.qdrant_service import QdrantService, QdrantVectorStoreManager
from app.services.gemini_chat import GeminiChatClient
from app.core.config import settings
from app.services.websocket_manager import manager


class DocumentIngestionManager:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.parser = DocumentParser()
        self.chunker = LegalHierarchicalChunker()
        self.emb_client = GeminiEmbeddingClient()
        self.qdrant_service = QdrantService()
        self.vector_store_manager = QdrantVectorStoreManager()
        self.chat_client = GeminiChatClient()

    async def _update_status(self, doc_meta: DocumentMetadata, status: str):
        doc_meta.status = status
        await self.db.commit()
        # Broadcast the status update to connected WebSocket clients
        await manager.broadcast({
            "document_id": doc_meta.id,
            "filename": doc_meta.filename,
            "status": status
        })

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
        LlamaIndex-native ingestion pipeline:
        1. Parse document via LlamaParse → LlamaIndex Documents
        2. Extract LLM metadata (case_name, court, date, statute_reference)
        3. Hierarchical chunking → parent/child/leaf TextNodes
        4. Batch embed leaf nodes via HuggingFaceEmbedding
        5. Upsert all nodes (with embeddings on leaves) into Qdrant
        Updates DocumentMetadata status in DB throughout.
        """
        # Fetch document metadata
        result = await self.db.execute(select(DocumentMetadata).where(DocumentMetadata.id == document_id))
        doc_meta = result.scalar_one_or_none()
        if not doc_meta:
            raise HTTPException(status_code=404, detail="Document metadata not found")

        try:
            # Step 1: Update status to processing
            await self._update_status(doc_meta, "processing 0%")

            # Step 2: Parse file into LlamaIndex Documents
            documents = await asyncio.get_running_loop().run_in_executor(
                None, self.parser.parse_file_to_documents, file_path
            )
            if not documents or not any(doc.text.strip() for doc in documents):
                raise ValueError("Parsed document is empty")

            await self._update_status(doc_meta, "processing 10%")

            # Step 3: Extract global metadata via LLM
            # Convert to legacy page format for metadata extraction
            pages = [{"page_number": doc.metadata.get("page_number", 1), "text": doc.text} for doc in documents]
            global_metadata = await self._extract_metadata_from_pages(pages, doc_meta.filename)

            # Merge workspace/document_type/industry/jurisdiction/state from DB record
            if doc_meta.workspace:
                global_metadata["workspace"] = doc_meta.workspace

            # Add document_id and filename to metadata for Qdrant filtering
            global_metadata["document_id"] = doc_meta.id
            global_metadata["filename"] = doc_meta.filename

            await self._update_status(doc_meta, "processing 20%")

            # Step 4: Hierarchical chunking via LlamaIndex HierarchicalNodeParser
            all_nodes = await asyncio.get_running_loop().run_in_executor(
                None, self.chunker.chunk_documents, documents, global_metadata
            )

            # Separate leaf nodes (for embedding) from parent/child nodes (stored for context retrieval)
            leaf_nodes = self.chunker.get_leaf_nodes(all_nodes)
            parent_nodes = self.chunker.get_parent_nodes(all_nodes)

            await self._update_status(doc_meta, "processing 30%")

            # Step 5: Batch embed leaf nodes
            leaf_texts = [node.get_content() for node in leaf_nodes]
            batch_size = 50
            embeddings = []

            for i in range(0, len(leaf_texts), batch_size):
                if i > 0:
                    await asyncio.sleep(0.5)  # rate limit pacing
                batch_texts = leaf_texts[i:i + batch_size]
                batch_embeddings = await self.emb_client.get_embeddings_batch(batch_texts)
                embeddings.extend(batch_embeddings)

                progress = 30 + int((len(embeddings) / max(len(leaf_texts), 1)) * 50)
                await self._update_status(doc_meta, f"processing {progress}%")

            # Assign embeddings to leaf nodes
            for idx, node in enumerate(leaf_nodes):
                node.embedding = embeddings[idx]

            # Step 6: Prepare and upsert Qdrant points
            collection_name = settings.QDRANT_COLLECTION
            doc_meta.qdrant_collection_name = collection_name

            # Ensure collection exists
            exists = await self.qdrant_service.collection_exists(collection_name)
            if not exists:
                await self.qdrant_service.create_collection(
                    collection_name, vector_size=settings.EMBEDDING_DIMENSION
                )

            # Build points for all nodes
            points = []

            # Leaf nodes: have embeddings, stored with full vector
            for node in leaf_nodes:
                payload = {
                    "document_id": doc_meta.id,
                    "filename": doc_meta.filename,
                    "text": node.get_content(),
                    "node_type": "leaf",
                    "node_id": node.node_id,
                }
                # Add hierarchical relationship metadata
                if node.parent_node:
                    payload["parent_node_id"] = node.parent_node.node_id
                # Add all node metadata (includes global_metadata)
                payload.update(node.metadata)

                points.append({
                    "id": str(uuid.uuid4()),
                    "vector": node.embedding,
                    "payload": payload
                })

            # Parent/child nodes: stored without embeddings (use zero vector as placeholder)
            # These are stored for context retrieval — when a leaf is matched,
            # we can fetch its parent for broader context
            zero_vector = [0.0] * settings.EMBEDDING_DIMENSION
            for node in all_nodes:
                if node not in leaf_nodes:
                    payload = {
                        "document_id": doc_meta.id,
                        "filename": doc_meta.filename,
                        "text": node.get_content(),
                        "node_type": "parent",
                        "node_id": node.node_id,
                    }
                    # Add child references
                    if hasattr(node, 'child_nodes') and node.child_nodes:
                        payload["child_node_ids"] = [child.node_id for child in node.child_nodes]
                    payload.update(node.metadata)

                    points.append({
                        "id": str(uuid.uuid4()),
                        "vector": zero_vector,
                        "payload": payload
                    })

            await self._update_status(doc_meta, "processing 85%")

            # Upsert in batches to avoid oversized requests
            upsert_batch_size = 100
            for i in range(0, len(points), upsert_batch_size):
                batch = points[i:i + upsert_batch_size]
                await self.qdrant_service.upsert_points(collection_name, batch)

            # Step 7: Update DB status to completed
            await self._update_status(doc_meta, "completed")

            print(f"[OK] Ingestion complete: {doc_meta.filename} | "
                  f"{len(leaf_nodes)} leaf nodes, {len(parent_nodes)} parent nodes, "
                  f"{len(all_nodes)} total nodes indexed into '{collection_name}'")

        except Exception as e:
            # Handle failure
            import traceback
            print(f"[ERROR] Ingestion pipeline failed for {doc_meta.filename}: {str(e)}")
            traceback.print_exc()
            await self._update_status(doc_meta, "failed")
            # Do NOT raise HTTPException in a background task, as the HTTP response 
            # has already been sent to the client, leading to a RuntimeError.
