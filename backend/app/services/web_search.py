from __future__ import annotations
from typing import List, TypedDict
from ..config import settings

class WebResult(TypedDict):
    title: str
    url: str
    snippet: str

class WebSearchProvider:
    async def search(self, query: str) -> List[WebResult]:
        raise NotImplementedError

class DummySearchProvider(WebSearchProvider):
    async def search(self, query: str) -> List[WebResult]:
        if not settings.web_search_enabled:
            return []
        return [
            {"title": "Example Result", "url": "https://example.com", "snippet": f"No real search. Your query: {query}"}
        ]

async def get_provider() -> WebSearchProvider:
    # Future: switch on settings.web_search_provider
    return DummySearchProvider()
