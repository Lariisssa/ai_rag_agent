from __future__ import annotations
from typing import Any, Dict, List, Literal
import asyncio
import httpx
import os
from ..config import settings

# Simple OpenAI-compatible client with fallback stubs when no API key.

class LLMClient:
    def __init__(self) -> None:
        self.api_key = settings.openai_api_key or os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

    async def chat(self, model: Literal['gpt-5','gpt-5-mini'], messages: List[Dict[str, str]], **kwargs: Any) -> str:
        if not self.api_key:
            # Fallback: echo last user message
            user_msgs = [m for m in messages if m.get('role') == 'user']
            return (user_msgs[-1]['content'] if user_msgs else '')[:200]
        # Map placeholder model names to a valid OpenAI model
        real_model = model
        if model in ("gpt-5", "gpt-5-mini"):
            real_model = "gpt-4o-mini"
        payload = {"model": real_model, "messages": messages, "temperature": kwargs.get("temperature", 0.2)}
        async with httpx.AsyncClient(timeout=30.0) as client:
            r = await client.post(f"{self.base_url}/chat/completions", headers={"Authorization": f"Bearer {self.api_key}"}, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def embed(self, texts: List[str]) -> List[List[float]]:
        if not self.api_key:
            # Deterministic tiny vectors as placeholder
            return [[(float((hash(t) % 1000)) / 1000.0) for _ in range(8)] for t in texts]
        async with httpx.AsyncClient(timeout=60.0) as client:
            r = await client.post(
                f"{self.base_url}/embeddings",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={"model": "text-embedding-3-large", "input": texts},
            )
            r.raise_for_status()
            data = r.json()
            return [item["embedding"] for item in data["data"]]

    async def stream_chat(self, model: Literal['gpt-5','gpt-5-mini'], messages: List[Dict[str, str]]):
        # For MVP, chunk the non-stream chat response into tokens
        text = await self.chat(model, messages)
        for tok in text.split():
            yield tok + ' '
            await asyncio.sleep(0.02)

llm_client = LLMClient()
