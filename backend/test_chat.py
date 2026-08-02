import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.chat_service import LegalChatService
import traceback

async def test():
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as session:
        try:
            chat_service = LegalChatService(session)
            print("Retrieving context...")
            # We use an empty filter to test if Qdrant search works
            chunks = await chat_service.retrieval_service.retrieve_context("what is the legal definition of cheating", limit=2, filters=None)
            print(f"Chunks retrieved: {len(chunks)}")
            
            print("Testing Gemini stream...")
            history = [{"role": "user", "content": "hello"}]
            async for chunk in chat_service.gemini_client.generate_response_stream(history, "System Prompt"):
                print(chunk, end="", flush=True)
            print("\nDone Gemini stream.")
            
        except Exception as e:
            traceback.print_exc()

asyncio.run(test())
