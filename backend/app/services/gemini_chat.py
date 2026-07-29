import httpx
from typing import List, Dict, Any
from fastapi import HTTPException
from app.core.config import settings

class GeminiChatClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        
        self.model = "gemini-1.5-flash"
        self.url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"
        
    async def generate_response(
        self, 
        messages: List[Dict[str, str]], 
        system_instruction: str = "You are a helpful assistant."
    ) -> str:
        """
        messages format:
        [
            {"role": "user", "content": "hello"},
            {"role": "model", "content": "hi there!"}
        ]
        """
        formatted_contents = []
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            formatted_contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
            
        payload = {
            "contents": formatted_contents,
            "systemInstruction": {
                "parts": [{"text": system_instruction}]
            },
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 2048
            }
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.url, 
                    json=payload, 
                    headers={"Content-Type": "application/json"},
                    timeout=60.0
                )
                response.raise_for_status()
                data = response.json()
                
                # Extract response text
                candidates = data.get("candidates", [])
                if not candidates:
                    raise ValueError("No response candidates returned from Gemini")
                    
                text_content = candidates[0]["content"]["parts"][0]["text"]
                return text_content
            except Exception as e:
                raise HTTPException(
                    status_code=500, 
                    detail=f"Gemini Generation API error: {str(e)}"
                )
