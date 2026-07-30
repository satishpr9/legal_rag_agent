import httpx
from typing import List, Dict, Any
from fastapi import HTTPException
from app.core.config import settings

class GeminiChatClient:
    def __init__(self):
        self.openai_api_key = settings.OPENAI_API_KEY
        self.gemini_api_key = settings.GEMINI_API_KEY
        
        self.openai_model = getattr(settings, "OPENAI_MODEL", "gpt-4o")
        self.gemini_model = getattr(settings, "GEMINI_MODEL", "gemini-2.5-flash")
        
        fallback_candidates = ["gemini-2.5-flash", "gemini-3.5-flash", "gemini-2.0-flash", "gemini-2.0-flash-lite"]
        self.gemini_models = [self.gemini_model] + [m for m in fallback_candidates if m != self.gemini_model]

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
        # 1. Use OpenAI if OPENAI_API_KEY is set
        if self.openai_api_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_api_key)
                
                messages_payload = [{"role": "system", "content": system_instruction}]
                for msg in messages:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages_payload.append({"role": role, "content": msg["content"]})

                response = await client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages_payload,
                    temperature=0.2,
                    max_tokens=2048
                )
                return response.choices[0].message.content
            except Exception as e:
                # If OpenAI throws an exception and Gemini key is available, fallback to Gemini
                if not self.gemini_api_key:
                    raise HTTPException(status_code=500, detail=f"OpenAI Generation API error: {str(e)}")

        # 2. Fallback / Primary Gemini implementation
        if not self.gemini_api_key:
            raise ValueError("Neither OPENAI_API_KEY nor GEMINI_API_KEY is set in environment")

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
            for model in self.gemini_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={self.gemini_api_key}"
                try:
                    response = await client.post(
                        url, 
                        json=payload, 
                        headers={"Content-Type": "application/json"},
                        timeout=60.0
                    )
                    response.raise_for_status()
                    data = response.json()
                    
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise ValueError("No response candidates returned from Gemini")
                        
                    text_content = candidates[0]["content"]["parts"][0]["text"]
                    return text_content
                except httpx.HTTPStatusError as err:
                    last_exception = err
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
            detail=f"AI Generation API error: {str(last_exception)}"
        )

    async def generate_response_stream(
        self,
        messages: List[Dict[str, str]],
        system_instruction: str = "You are a helpful assistant."
    ):
        """
        Yields text content chunks asynchronously as they stream from OpenAI or Gemini.
        """
        import json

        # 1. Stream via OpenAI if OPENAI_API_KEY is available
        if self.openai_api_key:
            try:
                from openai import AsyncOpenAI
                client = AsyncOpenAI(api_key=self.openai_api_key)
                
                messages_payload = [{"role": "system", "content": system_instruction}]
                for msg in messages:
                    role = "user" if msg["role"] == "user" else "assistant"
                    messages_payload.append({"role": role, "content": msg["content"]})

                stream = await client.chat.completions.create(
                    model=self.openai_model,
                    messages=messages_payload,
                    temperature=0.2,
                    max_tokens=2048,
                    stream=True
                )
                async for chunk in stream:
                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta.content
                        if delta:
                            yield delta
                return
            except Exception as openai_err:
                if not self.gemini_api_key:
                    raise HTTPException(status_code=500, detail=f"OpenAI Streaming API error: {str(openai_err)}")

        # 2. Stream via Gemini
        if not self.gemini_api_key:
            raise ValueError("Neither OPENAI_API_KEY nor GEMINI_API_KEY is set in environment")

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
            for model in self.gemini_models:
                url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:streamGenerateContent?alt=sse&key={self.gemini_api_key}"
                try:
                    async with client.stream("POST", url, json=payload, headers={"Content-Type": "application/json"}, timeout=60.0) as response:
                        if response.status_code in (404, 429, 503):
                            last_exception = f"Status {response.status_code}"
                            continue
                        response.raise_for_status()

                        async for line in response.aiter_lines():
                            if line.startswith("data: "):
                                data_str = line[6:].strip()
                                if not data_str:
                                    continue
                                try:
                                    chunk_data = json.loads(data_str)
                                    candidates = chunk_data.get("candidates", [])
                                    if candidates:
                                        parts = candidates[0].get("content", {}).get("parts", [])
                                        for p in parts:
                                            if "text" in p:
                                                yield p["text"]
                                except Exception:
                                    continue
                        return
                except Exception as e:
                    last_exception = e
                    continue

        # Fallback to single call
        try:
            full_text = await self.generate_response(messages, system_instruction)
            yield full_text
        except Exception:
            raise HTTPException(status_code=500, detail=f"Streaming API error: {str(last_exception)}")



