import os
from docx import Document
from fastapi import HTTPException
from llama_parse import LlamaParse
import asyncio
from app.core.config import settings

class DocumentParser:
    @staticmethod
    async def parse_pdf_pages(file_path: str) -> list[dict[str, any]]:
        try:
            if not settings.LLAMA_CLOUD_API_KEY:
                raise ValueError("LLAMA_CLOUD_API_KEY is missing from environment or .env file.")
                
            parser = LlamaParse(
                api_key=settings.LLAMA_CLOUD_API_KEY, 
                result_type="markdown"
            )
            documents = await parser.aload_data(file_path)
            pages = []
            for idx, doc in enumerate(documents):
                pages.append({
                    "page_number": idx + 1,
                    "text": doc.text
                })
            return pages
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")

    @staticmethod
    async def parse_pdf(file_path: str) -> str:
        pages = await DocumentParser.parse_pdf_pages(file_path)
        return "\n".join(p["text"] for p in pages if p["text"])

    @staticmethod
    def parse_docx(file_path: str) -> str:
        try:
            doc = Document(file_path)
            text = []
            for paragraph in doc.paragraphs:
                text.append(paragraph.text)
            return "\n".join(text)
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse DOCX: {str(e)}")

    @staticmethod
    def parse_txt(file_path: str) -> str:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse TXT: {str(e)}")

    @classmethod
    async def parse_file(cls, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return await cls.parse_pdf(file_path)
        elif ext == ".docx":
            return cls.parse_docx(file_path)
        elif ext in [".txt", ".md"]:
            return cls.parse_txt(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    @classmethod
    async def parse_file_pages(cls, file_path: str) -> list[dict[str, any]]:
        """
        Parses a document into page-level dictionaries: [{"page_number": 1, "text": "..."}]
        """
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return await cls.parse_pdf_pages(file_path)
        else:
            text = await cls.parse_file(file_path)
            return [{"page_number": 1, "text": text}]

