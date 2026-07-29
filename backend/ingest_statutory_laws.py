import os
import asyncio
from sqlalchemy.future import select
from app.db.session import AsyncSessionLocal
from app.db.models import DocumentMetadata
from app.services.ingestion import DocumentIngestionManager

UPLOAD_DIR = os.path.join(os.path.dirname(__file__), "uploads")

FILENAME_MAP = {
    "a202345.pdf": "Bharatiya Nyaya Sanhita (BNS), 2023.pdf",
}

async def ingest_all():
    print(f"Scanning files in {UPLOAD_DIR}...")
    if not os.path.exists(UPLOAD_DIR):
        print("Uploads directory not found.")
        return

    files = [f for f in os.listdir(UPLOAD_DIR) if f.lower().endswith(('.pdf', '.docx', '.txt'))]
    print(f"Found {len(files)} document(s): {files}")

    async with AsyncSessionLocal() as session:
        ingestion_manager = DocumentIngestionManager(session)

        for filename in files:
            file_path = os.path.join(UPLOAD_DIR, filename)
            display_name = FILENAME_MAP.get(filename, filename)

            # Check if document already exists and is completed
            result = await session.execute(
                select(DocumentMetadata).where(
                    (DocumentMetadata.filename == filename) | (DocumentMetadata.filename == display_name)
                )
            )
            existing_doc = result.scalar_one_or_none()

            if existing_doc and existing_doc.status == "completed":
                print(f"[SKIP] '{display_name}' is already fully ingested.")
                continue

            if not existing_doc:
                db_doc = DocumentMetadata(
                    filename=display_name,
                    status="processing 0%"
                )
                session.add(db_doc)
                await session.commit()
                await session.refresh(db_doc)
            else:
                db_doc = existing_doc
                db_doc.filename = display_name
                db_doc.status = "processing 0%"
                await session.commit()

            print(f"[INGESTING] Starting ingestion for '{display_name}' (ID: {db_doc.id})...")
            try:
                await ingestion_manager.ingest_document(document_id=db_doc.id, file_path=file_path)
                print(f"[SUCCESS] Finished ingesting '{display_name}'.")
            except Exception as e:
                print(f"[ERROR] Failed to ingest '{display_name}': {e}")

if __name__ == "__main__":
    asyncio.run(ingest_all())
