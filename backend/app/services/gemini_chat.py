import httpx
from typing import List, Dict, Any
from fastapi import HTTPException
from app.core.config import settings

class GeminiChatClient:
    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY environment variable is not set")
        primary_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        
        # Candidate models list in priority order
        fallback_candidates = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        self.models = [primary_model] + [m for m in fallback_candidates if m != primary_model]
        
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
        
        last_exception = None
        async with httpx.AsyncClient() as client:
            for model in self.models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.api_key}"
                try:
                    response = await client.post(
                        url, 
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
                except httpx.HTTPStatusError as err:
                    last_exception = err
                    # Fallthrough on 404 (model deprecated) or 429 (rate limit)
                    if err.response.status_code in (404, 429, 503):
                        continue
                    raise HTTPException(
                        status_code=500,
                        detail=f"Gemini Generation API error ({err.response.status_code}): {err.response.text}"
                    )
                except Exception as e:
                    last_exception = e
                    continue

        raise HTTPException(
            status_code=500, 
            detail=f"Gemini Generation API error: {str(last_exception)}"
        )

