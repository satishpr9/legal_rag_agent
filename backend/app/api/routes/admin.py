from fastapi import APIRouter, Depends, BackgroundTasks, HTTPException, File, UploadFile
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
    # Create document metadata
    db_doc = DocumentMetadata(
        filename=ingest_in.filename,
        status="pending"
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
    file: UploadFile = File(...)
):
    """
    Upload a local file and ingest it. Superuser only.
    """
    # Validate file extension
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in [".pdf", ".docx", ".txt"]:
        raise HTTPException(status_code=400, detail="Unsupported file format. Only PDF, DOCX, and TXT are supported.")

    # Sanitize and save the file
    sanitized_filename = os.path.basename(file.filename)
    saved_path = os.path.join(UPLOAD_DIR, sanitized_filename)
    
    with open(saved_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Create document metadata
    db_doc = DocumentMetadata(
        filename=file.filename,
        status="pending"
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
