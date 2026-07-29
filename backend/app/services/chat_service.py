from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException
from typing import List, Dict, Any

from app.db.models import ChatSession, ChatMessage
from app.services.search_service import LegalRetrievalService
from app.services.gemini_chat import GeminiChatClient

class LegalChatService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.retrieval_service = LegalRetrievalService()
        self.gemini_client = GeminiChatClient()

    async def get_session_history(self, session_id: int, user_id: int) -> List[Dict[str, str]]:
        """
        Retrieves the message history of a chat session formatted for Gemini.
        """
        result = await self.db.execute(
            select(ChatMessage)
            .where(ChatMessage.session_id == session_id)
            .order_by(ChatMessage.created_at.asc())
        )
        messages = result.scalars().all()
        
        return [
            {"role": msg.role, "content": msg.content}
            for msg in messages
        ]

    async def process_message(
        self, 
        session_id: int, 
        user_id: int, 
        user_content: str
    ) -> ChatMessage:
        """
        Executes the RAG-grounded chat loop:
        1. Retrieves relevant legal chunks.
        2. Formats RAG legal context.
        3. Formats chat history.
        4. Calls Gemini.
        5. Saves both user and assistant messages to database.
        """
        # Step 1: Verify session ownership
        session_result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        chat_session = session_result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Step 2: Retrieve relevant legal context from Qdrant
        retrieved_chunks = await self.retrieval_service.retrieve_context(
            query=user_content,
            limit=5
        )

        # Step 3: Format the context text for the System Prompt
        formatted_context = ""
        for i, chunk in enumerate(retrieved_chunks):
            formatted_context += f"--- Source Chunk {i+1} ---\n"
            formatted_context += f"Section: {chunk['estimated_section']}\n"
            formatted_context += f"Content: {chunk['text']}\n\n"

        # Step 4: Construct the legal RAG system prompt
        system_instruction = (
            "You are a highly experienced and meticulous Legal AI Assistant. Your goal is to help "
            "lawyers analyze contracts, documents, and case laws with absolute precision.\n\n"
            f"Here is the retrieved legal context from the workspace:\n{formatted_context}\n"
            "Instructions:\n"
            "1. Answer the user's query using ONLY the provided Retrieved Context.\n"
            "2. If the context does not contain the answer, say 'I cannot find the answer in the provided documents.' "
            "Do not invent facts or hallucinate.\n"
            "3. Be highly professional, clear, and organize your response carefully using bullet points and bolding.\n"
            "4. When citing information, explicitly reference the specific Section/Clause (e.g., 'According to Section 4.2...')."
        )

        # Step 5: Save the user's message to Postgres
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_content
        )
        self.db.add(user_message)
        await self.db.commit()

        # Step 6: Fetch historical messages
        history = await self.get_session_history(session_id, user_id)

        # Step 7: Call Gemini with the history and system prompt
        assistant_content = await self.gemini_client.generate_response(
            messages=history,
            system_instruction=system_instruction
        )

        # Step 8: Save assistant response (along with retrieved context payloads!) to Postgres
        assistant_message = ChatMessage(
            session_id=session_id,
            role="model",
            content=assistant_content,
            retrieved_context=retrieved_chunks
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)

        return assistant_message
