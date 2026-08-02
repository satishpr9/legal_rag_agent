import asyncio
import os
from fpdf import FPDF
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.db.models import DocumentMetadata
from app.services.ingestion import DocumentIngestionManager
from app.core.config import settings

def create_test_pdf():
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", size=12)
    pdf.cell(200, 10, txt="This is a simple test document for testing PDF ingestion.", ln=1, align="C")
    pdf.output("test.pdf")

async def test_ingestion():
    create_test_pdf()
    print("Created test.pdf")
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        # Create metadata entry
        doc_meta = DocumentMetadata(
            filename="test.pdf",
            workspace="Test Workspace",
            document_type="Test",
            industry="Test Industry",
            jurisdiction="State",
            state="Delhi",
            status="processing 0%"
        )
        session.add(doc_meta)
        await session.commit()
        await session.refresh(doc_meta)
        print(f"Created metadata with ID {doc_meta.id}")
        
        manager = DocumentIngestionManager(session)
        try:
            print("Starting ingestion...")
            await manager.ingest_document(doc_meta.id, "test.pdf")
            print("Ingestion completed successfully!")
            
            # Verify status
            await session.refresh(doc_meta)
            print(f"Final status in DB: {doc_meta.status}")
        except Exception as e:
            print(f"Ingestion failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_ingestion())
