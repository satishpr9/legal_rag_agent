import asyncio
from app.core.config import settings
from llama_parse import LlamaParse

async def test_parse():
    try:
        print("Initializing LlamaParse...")
        parser = LlamaParse(
            api_key=settings.LLAMA_CLOUD_API_KEY, 
            result_type="markdown"
        )
        print("Uploading test.pdf to LlamaCloud...")
        documents = await parser.aload_data("test.pdf")
        print(f"Successfully parsed {len(documents)} pages!")
        print("First page preview:")
        print(documents[0].text[:100])
    except Exception as e:
        print(f"Error: {e}")

asyncio.run(test_parse())
