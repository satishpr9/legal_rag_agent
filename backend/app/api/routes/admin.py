from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, File, UploadFile, Form
from typing import Optional
from app.api.deps import SessionDep, SuperUserDep
from app.db.models import DocumentMetadata, User
from app.schemas.document import DocumentIngestRequest, DocumentMetadataResponse
from app.schemas.user import UserResponse
from app.services.ingestion import DocumentIngestionManager
from app.api.deps import CurrentUser
from sqlalchemy.future import select
import os
import shutil

router = APIRouter()

@router.get("/users", response_model=list[UserResponse])
async def list_users(
    session: SessionDep,
    current_user: SuperUserDep
):
    """
    List all users in the system. Admin only.
    """
    result = await session.execute(select(User).order_by(User.created_at.desc()))
    return result.scalars().all()

@router.post("/documents/ingest", response_model=DocumentMetadataResponse)
async def ingest_document(
    ingest_in: DocumentIngestRequest,
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: SuperUserDep
):
    """
    Trigger ingestion of a backend file. Superuser only.
    """
    # Check if document already exists
    result = await session.execute(select(DocumentMetadata).where(DocumentMetadata.filename == ingest_in.filename))
    existing_doc = result.scalar_one_or_none()
    if existing_doc:
        raise HTTPException(status_code=400, detail=f"A document with the name '{ingest_in.filename}' has already been uploaded.")

    # Create document metadata
    db_doc = DocumentMetadata(
        filename=ingest_in.filename,
        status="processing 0%"
    )
    session.add(db_doc)
    await session.commit()
    await session.refresh(db_doc)

    # Ingest document in background
    ingestion_manager = DocumentIngestionManager(session)
    background_tasks.add_task(
        ingestion_manager.ingest_document,
        document_id=db_doc.id,
        file_path=ingest_in.file_path
    )

    return db_doc

@router.get("/documents", response_model=list[DocumentMetadataResponse])
async def list_documents(
    session: SessionDep,
    current_user: CurrentUser
):
    """
    List all documents. Available to all authenticated users.
    """
    result = await session.execute(
        select(DocumentMetadata)
        .order_by(DocumentMetadata.created_at.desc())
    )
    return result.scalars().all()

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/documents/upload", response_model=DocumentMetadataResponse)
async def upload_document(
    background_tasks: BackgroundTasks,
    session: SessionDep,
    current_user: SuperUserDep,
    file: UploadFile = File(...),
    workspace: Optional[str] = Form(None),
    document_type: Optional[str] = Form(None),
    industry: Optional[str] = Form(None),
    jurisdiction: Optional[str] = Form(None),
    state: Optional[str] = Form(None)
):
    """
    Upload a local file and ingest it. Superuser only.
    """
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Only PDF, DOCX, and TXT are supported.")

    # Check if document already exists
    result = await session.execute(select(DocumentMetadata).where(DocumentMetadata.filename == file.filename))
    existing_doc = result.scalar_one_or_none()
    if existing_doc:
        raise HTTPException(status_code=400, detail=f"A document with the name '{file.filename}' has already been uploaded.")

    # Sanitize and save the file
    sanitized_filename = os.path.basename(file.filename)
    saved_path = os.path.join(UPLOAD_DIR, sanitized_filename)
    
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create document metadata
    db_doc = DocumentMetadata(
        filename=file.filename,
        workspace=workspace,
        document_type=document_type,
        industry=industry,
        jurisdiction=jurisdiction,
        state=state,
        status="processing 0%"
    )
    session.add(db_doc)
    await session.commit()
    await session.refresh(db_doc)

    # Ingest document in background
    ingestion_manager = DocumentIngestionManager(session)
    background_tasks.add_task(
        ingestion_manager.ingest_document,
        document_id=db_doc.id,
        file_path=saved_path
    )

    return db_doc

@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: int,
    session: SessionDep,
    current_user: SuperUserDep
):
    """
    Delete a document from DB and purge vectors from Qdrant. Superuser only.
    """
    result = await session.execute(select(DocumentMetadata).where(DocumentMetadata.id == document_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")

    # Purge vectors from Qdrant
    try:
        from app.services.qdrant_service import QdrantService
        from app.core.config import settings
        qdrant_service = QdrantService()
        collection_name = doc.qdrant_collection_name or settings.QDRANT_COLLECTION_NAME
        await qdrant_service.delete_document_points(collection_name, document_id)
    except Exception:
        pass

    await session.delete(doc)
    await session.commit()
    return {"status": "success", "message": f"Document {document_id} deleted successfully"}

@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    session: SessionDep,
    current_user: SuperUserDep
):
    """
    Delete a user. Superuser only. Cannot delete self.
    """
    if current_user.id == user_id:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    result = await session.execute(select(User).where(User.id == user_id))
    user_to_delete = result.scalar_one_or_none()
    if not user_to_delete:
        raise HTTPException(status_code=404, detail="User not found")

    await session.delete(user_to_delete)
    await session.commit()
    return {"status": "success", "message": f"User {user_id} deleted successfully"}
