from fastapi import APIRouter, Depends, HTTPException
from app.api.deps import SessionDep, CurrentUser
from app.db.models import ChatSession, ChatMessage, RoleEnum
from app.schemas.chat import ChatSessionCreate, ChatSessionResponse, ChatMessageCreate, ChatMessageResponse
from app.services.chat_service import LegalChatService
from sqlalchemy.future import select

router = APIRouter()

def check_not_admin(user):
    pass

@router.post("/sessions", response_model=ChatSessionResponse)
async def create_chat_session(
    session_in: ChatSessionCreate,
    session: SessionDep,
    current_user: CurrentUser
):
    """
    Create a new chat session globally.
    """
    check_not_admin(current_user)
    db_session = ChatSession(
        user_id=current_user.id,
        title=session_in.title
    )
    session.add(db_session)
    await session.commit()
    await session.refresh(db_session)
    return db_session

@router.get("/sessions", response_model=list[ChatSessionResponse])
async def list_chat_sessions(
    session: SessionDep,
    current_user: CurrentUser
):
    """
    List all chat sessions for the current user.
    """
    check_not_admin(current_user)
    result = await session.execute(
        select(ChatSession)
        .where(ChatSession.user_id == current_user.id)
        .order_by(ChatSession.created_at.desc())
    )
    return result.scalars().all()

@router.get("/sessions/{session_id}/messages", response_model=list[ChatMessageResponse])
async def get_chat_messages(
    session_id: int,
    session: SessionDep,
    current_user: CurrentUser
):
    """
    Get all messages for a chat session.
    """
    check_not_admin(current_user)
    session_result = await session.execute(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == current_user.id)
    )
    chat_session = session_result.scalar_one_or_none()
    if not chat_session:
        raise HTTPException(status_code=404, detail="Chat session not found")
        
    result = await session.execute(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc())
    )
    return result.scalars().all()

@router.post("/sessions/{session_id}/messages", response_model=ChatMessageResponse)
async def send_message(
    session_id: int,
    msg_in: ChatMessageCreate,
    session: SessionDep,
    current_user: CurrentUser
):
    """
    Send a message and get a RAG-grounded response.
    """
    check_not_admin(current_user)
    chat_service = LegalChatService(session)
    response_msg = await chat_service.process_message(
        session_id=session_id,
        user_id=current_user.id,
        user_content=msg_in.content
    )
    return response_msg
