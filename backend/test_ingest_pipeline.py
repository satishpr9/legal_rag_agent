"""
End-to-end test for the LlamaIndex-based ingestion pipeline.
Creates a realistic legal PDF, ingests it via the new pipeline, 
and verifies hierarchical nodes in Qdrant.
"""
import asyncio
import os
import httpx
from fpdf import FPDF
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.future import select
from app.db.models import DocumentMetadata
from app.services.ingestion import DocumentIngestionManager
from app.core.config import settings


def create_legal_test_pdf(path: str = "test_legal.pdf"):
    """Creates a multi-page legal PDF with sections, articles, and structured content."""
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)

    # Page 1: Title and Preamble
    pdf.add_page()
    pdf.set_font("Arial", "B", 16)
    pdf.cell(0, 12, "THE BHARATIYA NYAYA SANHITA, 2023", ln=True, align="C")
    pdf.set_font("Arial", "", 10)
    pdf.cell(0, 8, "(Act No. 45 of 2023)", ln=True, align="C")
    pdf.ln(8)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6,
        "An Act to consolidate and amend the law relating to criminal offences "
        "and for matters connected therewith or incidental thereto.\n\n"
        "WHEREAS it is expedient to consolidate and amend the law relating to "
        "criminal offences in India;\n\n"
        "BE it enacted by Parliament in the Seventy-fourth Year of the Republic "
        "of India as follows:"
    )

    # Page 1: Chapter I
    pdf.ln(6)
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "CHAPTER I", ln=True)
    pdf.cell(0, 8, "PRELIMINARY", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "Section 1. Short title, commencement and application.", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6,
        "(1) This Act may be called the Bharatiya Nyaya Sanhita, 2023.\n"
        "(2) It shall come into force on such date as the Central Government may, "
        "by notification in the Official Gazette, appoint.\n"
        "(3) Every person shall be liable to punishment under this Sanhita and not "
        "otherwise for every act or omission contrary to the provisions thereof."
    )

    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "Section 2. Definitions.", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6,
        "In this Sanhita, unless the context otherwise requires:\n"
        "(a) 'act' includes a series of acts, and an illegal omission;\n"
        "(b) 'animal' means any living creature, other than a human being;\n"
        "(c) 'community service' means service in lieu of fine or as part of "
        "the sentence imposed by the court;\n"
        "(d) 'counterfeit' - A person is said to counterfeit who causes one thing "
        "to resemble another thing;\n"
        "(e) 'court' means a Judge or Magistrate who is empowered by law to act "
        "judicially;\n"
        "(f) 'death' means the death of a human being."
    )

    # Page 2: Chapter II - Punishments
    pdf.add_page()
    pdf.set_font("Arial", "B", 13)
    pdf.cell(0, 8, "CHAPTER II", ln=True)
    pdf.cell(0, 8, "PUNISHMENTS", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "Section 4. Punishments.", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6,
        "The punishments to which offenders are liable under the provisions "
        "of this Sanhita are:\n"
        "(a) Death;\n"
        "(b) Imprisonment for life;\n"
        "(c) Imprisonment (rigorous or simple);\n"
        "(d) Forfeiture of property;\n"
        "(e) Fine;\n"
        "(f) Community service."
    )

    pdf.ln(4)
    pdf.set_font("Arial", "B", 11)
    pdf.cell(0, 7, "Section 5. Commutation of sentence.", ln=True)
    pdf.set_font("Arial", "", 11)
    pdf.multi_cell(0, 6,
        "The appropriate Government may, without the consent of the offender, "
        "commute any of the following sentences for any other mentioned after it:\n"
        "(a) Death, for any other punishment provided under this Sanhita;\n"
        "(b) Imprisonment for life, for imprisonment not exceeding fourteen years;\n"
        "(c) Rigorous imprisonment, for simple imprisonment for a term not "
        "exceeding that term;\n"
        "(d) Simple imprisonment, for fine."
    )

    # Table of offences
    pdf.ln(6)
    pdf.set_font("Arial", "B", 12)
    pdf.cell(0, 8, "Schedule of Offences and Penalties", ln=True)
    pdf.set_font("Arial", "B", 10)

    col_w = [20, 60, 50, 50]
    headers = ["Section", "Offence", "Punishment", "Cognizable"]
    for i, h in enumerate(headers):
        pdf.cell(col_w[i], 7, h, border=1, align="C")
    pdf.ln()

    pdf.set_font("Arial", "", 9)
    rows = [
        ["103", "Murder", "Death or Life Imprisonment", "Yes"],
        ["105", "Culpable Homicide", "Life Imprisonment or 10 yrs", "Yes"],
        ["115", "Voluntarily causing hurt", "1 year or fine or both", "No"],
        ["303", "Theft", "3 years or fine or both", "No"],
        ["309", "Robbery", "10 years and fine", "Yes"],
    ]
    for row in rows:
        for i, cell in enumerate(row):
            pdf.cell(col_w[i], 6, cell, border=1)
        pdf.ln()

    pdf.output(path)
    return path


async def verify_qdrant_results(document_id: int):
    """Query Qdrant directly to verify hierarchical nodes were stored."""
    print("\n--- Qdrant Verification ---")

    async with httpx.AsyncClient() as client:
        # Check collection exists
        url = f"http://localhost:6333/collections/{settings.QDRANT_COLLECTION}"
        resp = await client.get(url, timeout=10.0)
        data = resp.json()
        if resp.status_code == 200:
            points_count = data.get("result", {}).get("points_count", 0)
            print(f"  Collection '{settings.QDRANT_COLLECTION}' exists, {points_count} total points")
        else:
            print(f"  ERROR: Collection not found!")
            return

        # Search for our document's points
        scroll_url = f"http://localhost:6333/collections/{settings.QDRANT_COLLECTION}/points/scroll"
        scroll_body = {
            "filter": {
                "must": [{"key": "document_id", "match": {"value": document_id}}]
            },
            "limit": 200,
            "with_payload": True,
            "with_vector": False
        }
        resp = await client.post(scroll_url, json=scroll_body, timeout=10.0)
        data = resp.json()
        points = data.get("result", {}).get("points", [])

        leaf_count = sum(1 for p in points if p["payload"].get("node_type") == "leaf")
        parent_count = sum(1 for p in points if p["payload"].get("node_type") == "parent")

        print(f"  Document {document_id} points: {len(points)} total ({leaf_count} leaf, {parent_count} parent)")

        # Show sample leaf node
        for p in points:
            if p["payload"].get("node_type") == "leaf":
                payload = p["payload"]
                text_preview = payload.get("text", "")[:120].replace("\n", " ")
                parent_id = payload.get("parent_node_id", "none")
                print(f"\n  Sample LEAF node:")
                print(f"    node_id: {payload.get('node_id', 'N/A')}")
                print(f"    parent_node_id: {parent_id}")
                print(f"    filename: {payload.get('filename')}")
                print(f"    text: {text_preview}...")
                break

        # Show sample parent node
        for p in points:
            if p["payload"].get("node_type") == "parent":
                payload = p["payload"]
                text_preview = payload.get("text", "")[:120].replace("\n", " ")
                print(f"\n  Sample PARENT node:")
                print(f"    node_id: {payload.get('node_id', 'N/A')}")
                print(f"    filename: {payload.get('filename')}")
                print(f"    text: {text_preview}...")
                break

        if leaf_count > 0 and parent_count > 0:
            print(f"\n  [OK] Hierarchical chunking verified: {leaf_count} leaf + {parent_count} parent nodes")
        elif leaf_count > 0:
            print(f"\n  [WARN] Only leaf nodes found ({leaf_count}). Document may be too short for parent nodes.")
        else:
            print(f"\n  [FAIL] No nodes found for this document!")


async def run_test():
    # Step 1: Create test PDF
    pdf_path = create_legal_test_pdf()
    abs_path = os.path.abspath(pdf_path)
    print(f"[OK] Created test legal PDF: {abs_path}")

    # Step 2: Connect to DB
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Clean up any previous test document
        result = await session.execute(
            select(DocumentMetadata).where(DocumentMetadata.filename == "test_legal.pdf")
        )
        existing = result.scalar_one_or_none()
        if existing:
            from app.services.qdrant_service import QdrantService
            qs = QdrantService()
            await qs.delete_document_points(settings.QDRANT_COLLECTION, existing.id)
            await session.delete(existing)
            await session.commit()
            print("  Cleaned up previous test document")

        # Step 3: Create DB metadata (only valid columns)
        doc_meta = DocumentMetadata(
            filename="test_legal.pdf",
            workspace="Test Workspace",
            status="processing 0%"
        )
        session.add(doc_meta)
        await session.commit()
        await session.refresh(doc_meta)
        print(f"[OK] Created DB metadata (ID: {doc_meta.id})")

        # Step 4: Run ingestion
        manager = DocumentIngestionManager(session)
        try:
            print("\n[RUNNING] Starting ingestion pipeline...")
            print("   (This may take a minute -- LlamaParse + embedding)")
            await manager.ingest_document(doc_meta.id, abs_path)

            await session.refresh(doc_meta)
            print(f"\n[OK] Ingestion complete! Final DB status: {doc_meta.status}")

        except Exception as e:
            await session.refresh(doc_meta)
            print(f"\n[FAIL] Ingestion FAILED: {e}")
            print(f"   DB status: {doc_meta.status}")
            import traceback
            traceback.print_exc()
            return

        # Step 5: Verify Qdrant
        await verify_qdrant_results(doc_meta.id)

    # Cleanup
    if os.path.exists(pdf_path):
        os.remove(pdf_path)
        print(f"\n[CLEANUP] Removed {pdf_path}")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_test())
