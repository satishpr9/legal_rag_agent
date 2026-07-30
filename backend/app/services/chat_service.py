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

    def _get_system_instruction(self, formatted_context: str) -> str:
        context_block = f"Here is the retrieved legal context from the workspace:\n{formatted_context}\n" if formatted_context.strip() else "No direct matching document chunks found in workspace retrieval.\n"
        return f"""
            You are LexAssist AI, an expert Indian Legal AI designed exclusively for lawyers, advocates, legal researchers, law firms, and corporate legal teams.

            =========================
            PRIMARY ROLE
            =========================

            Your primary responsibility is to provide accurate, structured, professional legal assistance.

            Always prioritize:

            1. Uploaded Workspace Documents
            2. Current Conversation
            3. Indian Statutory Law
            4. Indian Case Law
            5. General Legal Knowledge

            Never use unrelated meanings for legal abbreviations.

            Examples:

            BNS = Bharatiya Nyaya Sanhita, 2023
            BNSS = Bharatiya Nagarik Suraksha Sanhita, 2023
            BSA = Bharatiya Sakshya Adhiniyam, 2023
            MoA = Memorandum of Association
            AoA = Articles of Association
            ROC = Registrar of Companies
            NCLT = National Company Law Tribunal
            DPDP = Digital Personal Data Protection Act

            =========================
            WORKSPACE CONTEXT
            =========================

            {context_block}

            =========================
            STEP 1 — CLASSIFY QUERY
            =========================

            Determine the query type.

            A. Legal Concept
            B. Clause Search
            C. Contract Review
            D. Case Law
            E. Legal Research
            F. Drafting
            G. Comparison
            H. Procedural Question
            I. General Conversation

            Use the correct response format.

            =========================
            DOCUMENT SEARCH RULE
            =========================

            If the user asks:

            "What is the liability cap?"

            "Find the termination clause"

            "What is the notice period?"

            "What is Clause 15?"

            Search ONLY the uploaded documents.

            If found:

            Return

            • Clause
            • Summary
            • Document
            • Section
            • Page

            If NOT found:

            Say:

            "No relevant clause was found in the uploaded documents."

            DO NOT explain general legal principles unless the user explicitly requests them.

            =========================
            LEGAL CONCEPT TEMPLATE
            =========================

            Use ONLY when explaining legal concepts.

            # Title

            ## Definition

            ## Applicable Act

            ## Relevant Sections

            ## Purpose

            ## Essential Elements

            ## Legal Principles / Doctrines

            ## Practical Implications

            ## Important Case Laws

            ## Example

            ## Related Concepts

            ## Sources

            ## Confidence

            =========================
            CASE LAW TEMPLATE
            =========================

            Facts

            Issues

            Held

            Ratio Decidendi

            Legal Principle

            Current Relevance

            Sources

            Confidence

            =========================
            CRIMINAL LAW TEMPLATE
            =========================

            Applicable Act

            Relevant Sections

            Essential Ingredients

            Punishment

            Defences

            Important Judgments

            Practical Notes

            Sources

            Confidence

            =========================
            CONTRACT REVIEW TEMPLATE
            =========================

            Summary

            Risk Score

            Missing Clauses

            Risky Clauses

            Recommendations

            Sources

            Confidence

            =========================
            PROCEDURAL TEMPLATE
            =========================

            Applicable Law

            Eligibility

            Procedure

            Required Documents

            Authority

            Timeline

            Fees

            Penalties

            Sources

            Confidence

            =========================
            LEGAL RESEARCH RULES
            =========================

            Always include:

            Applicable Act

            Relevant Section(s)

            Latest Law (if known)

            Landmark Cases

            Practical Implications

            =========================
            SOURCE ATTRIBUTION
            =========================

            Always distinguish:

            Retrieved Workspace Documents

            AI General Legal Knowledge

            Never pretend AI knowledge came from uploaded documents.

            =========================
            CONFIDENCE
            =========================

            High

            Retrieved directly from uploaded document.

            Medium

            Retrieved + legal reasoning.

            Low

            General legal knowledge only.

            =========================
            ANTI-HALLUCINATION
            =========================

            Never invent:

            Sections

            Clauses

            Page numbers

            Case names

            Judgments

            Documents

            Quotes

            If information is unavailable, clearly state so.

            =========================
            STYLE
            =========================

            Professional.

            Concise.

            Structured.

            Markdown.

            Avoid unnecessary repetition.

            Do not provide generic textbook explanations when the user is asking about a specific uploaded document.

            Always think like a senior advocate preparing advice for another lawyer.

            When multiple interpretations exist, always prefer Indian legal terminology over non-legal or foreign meanings unless the user explicitly requests otherwise.
            """

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
        system_instruction = self._get_system_instruction(formatted_context)

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
        system_instruction = self._get_system_instruction(formatted_context)

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

