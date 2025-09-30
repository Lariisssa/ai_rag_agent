from __future__ import annotations
from typing import List
from .llm import LLMClient

client = LLMClient()

async def embed_texts(texts: List[str]) -> List[list[float]]:
    return await client.embed(texts)
