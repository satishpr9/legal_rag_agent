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

        # Auto-title session from user's first prompt if title is default
        if chat_session.title in ["New Chat", "New Consultation"]:
            first_line = user_content.strip().split('\n')[0][:40]
            if first_line:
                chat_session.title = first_line
                await self.db.commit()
                await self.db.refresh(chat_session)

        # Save user message to Postgres
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_content
        )
        self.db.add(user_message)
        await self.db.commit()

        # Step 2: Retrieve relevant legal context & historical messages concurrently
        import asyncio
        retrieved_chunks, history = await asyncio.gather(
            self.retrieval_service.retrieve_context(query=user_content, limit=4),
            self.get_session_history(session_id, user_id)
        )

        # Step 3: Format the context text for the System Prompt (with Document Name, Section, and Page Number)
        formatted_context = ""
        for i, chunk in enumerate(retrieved_chunks):
            doc_name = chunk.get("filename") or f"Document #{chunk.get('document_id')}"
            sec = chunk.get("estimated_section", "General")
            page = chunk.get("page_number", 1)
            formatted_context += f"--- Source Chunk {i+1} ---\n"
            formatted_context += f"Document: {doc_name}\n"
            formatted_context += f"Section: {sec}\n"
            formatted_context += f"Page: {page}\n"
            formatted_context += f"Content: {chunk['text']}\n\n"

        # Compute Confidence Level based on retrieval scores
        if retrieved_chunks and len(retrieved_chunks) > 0:
            top_score = retrieved_chunks[0].get("score", 0.0)
            if top_score >= 0.70:
                confidence_level = "High"
            elif top_score >= 0.45:
                confidence_level = "Medium"
            else:
                confidence_level = "Low"
        else:
            confidence_level = "Low"

        # Step 4: Construct the legal RAG system prompt
        context_block = f"Here is the retrieved legal context from the workspace:\n{formatted_context}\n" if formatted_context.strip() else "No direct matching document chunks found in workspace retrieval.\n"
        
        system_instruction = (
            "You are a highly experienced and meticulous Legal AI Assistant specializing in statutory laws, contracts, and legal analysis.\n\n"
            f"{context_block}"
            "Instructions:\n"
            "1. Primary Source & Citation: Ground your analysis in the provided Retrieved Context whenever available. "
            "When referencing specific provisions from the context, explicitly cite the Document name, Section/Clause, and Page number if provided (e.g., 'According to Bharatiya Nyaya Sanhita, Section 4 (Page 12)...').\n"
            "2. General Knowledge & Definitions: If the retrieved context is empty or incomplete for general legal definitions, statutory background (such as explaining abbreviations like BNS / Bharatiya Nyaya Sanhita, IPC, BNSS, BSA, etc.), or standard legal concepts, provide a clear, accurate, and professional legal overview using established legal knowledge. Clearly distinguish between workspace document citations and general legal background.\n"
            "3. Precision & Anti-Hallucination: Do not fabricate specific clause numbers or invent non-existent file references when citing workspace documents.\n"
            "4. Formatting: Be highly professional, concise, and structure your response with clear headers, bullet points, and bold key terms.\n"
            "5. Legal Disclaimer: Keep in mind that all responses are provided for informational and legal research purposes."
        )

        # Step 7: Call LLM with the history and system prompt
        assistant_content = await self.gemini_client.generate_response(
            messages=history,
            system_instruction=system_instruction
        )

        # Step 8: Save assistant response (along with retrieved context payloads & confidence level!) to Postgres
        assistant_message = ChatMessage(
            session_id=session_id,
            role="model",
            content=assistant_content,
            confidence_level=confidence_level,
            retrieved_context=retrieved_chunks
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)

        return assistant_message

    async def process_message_stream(
        self,
        session_id: int,
        user_id: int,
        user_content: str
    ):
        """
        Executes the RAG-grounded chat loop with real-time SSE token streaming.
        Yields JSON formatted SSE strings: data: {...}\n\n
        """
        import json

        # Step 1: Verify session ownership
        session_result = await self.db.execute(
            select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
        )
        chat_session = session_result.scalar_one_or_none()
        if not chat_session:
            raise HTTPException(status_code=404, detail="Chat session not found")

        # Auto-title session from user's first prompt if title is default
        if chat_session.title in ["New Chat", "New Consultation"]:
            first_line = user_content.strip().split('\n')[0][:40]
            if first_line:
                chat_session.title = first_line

        # Save user message to Postgres & commit session title
        user_message = ChatMessage(
            session_id=session_id,
            role="user",
            content=user_content
        )
        self.db.add(user_message)
        await self.db.commit()

        # Fetch history & retrieve legal context concurrently to minimize latency
        import asyncio
        history, retrieved_chunks = await asyncio.gather(
            self.get_session_history(session_id, user_id),
            self.retrieval_service.retrieve_context(query=user_content, limit=4)
        )

        # Step 3: Format the context text for System Prompt
        formatted_context = ""
        for i, chunk in enumerate(retrieved_chunks):
            doc_name = chunk.get("filename") or f"Document #{chunk.get('document_id')}"
            sec = chunk.get("estimated_section", "General")
            page = chunk.get("page_number", 1)
            formatted_context += f"--- Source Chunk {i+1} ---\n"
            formatted_context += f"Document: {doc_name}\n"
            formatted_context += f"Section: {sec}\n"
            formatted_context += f"Page: {page}\n"
            formatted_context += f"Content: {chunk['text']}\n\n"

        # Compute Confidence Level
        if retrieved_chunks and len(retrieved_chunks) > 0:
            top_score = retrieved_chunks[0].get("score", 0.0)
            if top_score >= 0.70:
                confidence_level = "High"
            elif top_score >= 0.45:
                confidence_level = "Medium"
            else:
                confidence_level = "Low"
        else:
            confidence_level = "Low"

        # Yield Initial Metadata Packet to Client
        meta_event = {
            "type": "metadata",
            "retrieved_context": retrieved_chunks,
            "confidence_level": confidence_level,
            "title": chat_session.title
        }
        yield f"data: {json.dumps(meta_event)}\n\n"

        # Construct legal RAG system prompt
        context_block = f"Here is the retrieved legal context from the workspace:\n{formatted_context}\n" if formatted_context.strip() else "No direct matching document chunks found in workspace retrieval.\n"
        
        system_instruction = (
            "You are a highly experienced and meticulous Legal AI Assistant specializing in statutory laws, contracts, and legal analysis.\n\n"
            f"{context_block}"
            "Instructions:\n"
            "1. Primary Source & Citation: Ground your analysis in the provided Retrieved Context whenever available. "
            "When referencing specific provisions from the context, explicitly cite the Document name, Section/Clause, and Page number if provided (e.g., 'According to Bharatiya Nyaya Sanhita, Section 4 (Page 12)...').\n"
            "2. General Knowledge & Definitions: If the retrieved context is empty or incomplete for general legal definitions, statutory background (such as explaining abbreviations like BNS / Bharatiya Nyaya Sanhita, IPC, BNSS, BSA, etc.), or standard legal concepts, provide a clear, accurate, and professional legal overview using established legal knowledge. Clearly distinguish between workspace document citations and general legal background.\n"
            "3. Precision & Anti-Hallucination: Do not fabricate specific clause numbers or invent non-existent file references when citing workspace documents.\n"
            "4. Formatting: Be highly professional, concise, and structure your response with clear headers, bullet points, and bold key terms.\n"
            "5. Legal Disclaimer: Keep in mind that all responses are provided for informational and legal research purposes."
        )

        # Stream assistant content from Gemini
        accumulated_text = ""
        async for chunk_text in self.gemini_client.generate_response_stream(
            messages=history,
            system_instruction=system_instruction
        ):
            accumulated_text += chunk_text
            chunk_event = {
                "type": "chunk",
                "content": chunk_text
            }
            yield f"data: {json.dumps(chunk_event)}\n\n"

        # Save assistant message to DB
        assistant_message = ChatMessage(
            session_id=session_id,
            role="model",
            content=accumulated_text,
            confidence_level=confidence_level,
            retrieved_context=retrieved_chunks
        )
        self.db.add(assistant_message)
        await self.db.commit()
        await self.db.refresh(assistant_message)

        done_event = {
            "type": "done",
            "message_id": assistant_message.id
        }
        yield f"data: {json.dumps(done_event)}\n\n"

