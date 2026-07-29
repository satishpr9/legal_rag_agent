import os
from pypdf import PdfReader
from docx import Document
from fastapi import HTTPException

class DocumentParser:
    @staticmethod
    def parse_pdf_pages(file_path: str) -> list[dict[str, any]]:
        try:
            reader = PdfReader(file_path)
            pages = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text() or ""
                pages.append({
                    "page_number": idx + 1,
                    "text": page_text
                })
            return pages
        except Exception as e:
            raise HTTPException(status_code=400, detail=f"Failed to parse PDF: {str(e)}")

    @staticmethod
    def parse_pdf(file_path: str) -> str:
        pages = DocumentParser.parse_pdf_pages(file_path)
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
    def parse_file(cls, file_path: str) -> str:
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return cls.parse_pdf(file_path)
        elif ext == ".docx":
            return cls.parse_docx(file_path)
        elif ext in [".txt", ".md"]:
            return cls.parse_txt(file_path)
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported file format: {ext}")

    @classmethod
    def parse_file_pages(cls, file_path: str) -> list[dict[str, any]]:
        """
        Parses a document into page-level dictionaries: [{"page_number": 1, "text": "..."}]
        """
        if not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="File not found")
        
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            return cls.parse_pdf_pages(file_path)
        else:
            text = cls.parse_file(file_path)
            return [{"page_number": 1, "text": text}]

