from __future__ import annotations
from typing import List, TypedDict
import httpx
import structlog
from ..config import settings

log = structlog.get_logger(__name__)

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

class TavilySearchProvider(WebSearchProvider):
    """Tavily AI Search - optimized for RAG/LLM use cases"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.tavily.com/search"

    async def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        if not settings.web_search_enabled:
            return []

        log.info("tavily_search_start", query=query, max_results=max_results)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.post(
                    self.base_url,
                    json={
                        "api_key": self.api_key,
                        "query": query,
                        "max_results": max_results,
                        "search_depth": "basic",  # "basic" or "advanced"
                        "include_answer": False,
                        "include_raw_content": False,
                    }
                )
                response.raise_for_status()
                data = response.json()

                results: List[WebResult] = []
                for item in data.get("results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", "Untitled"),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")[:500],  # Limit snippet size
                    })

                log.info("tavily_search_complete", query=query, count=len(results))
                return results
        except httpx.TimeoutException:
            log.warning("tavily_search_timeout", query=query)
            return []
        except httpx.HTTPStatusError as e:
            log.error("tavily_search_http_error", query=query, status=e.response.status_code, error=str(e))
            return []
        except Exception as e:
            log.error("tavily_search_error", query=query, error=str(e))
            return []

class BingSearchProvider(WebSearchProvider):
    """Bing Web Search API"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.bing.microsoft.com/v7.0/search"

    async def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        if not settings.web_search_enabled:
            return []

        log.info("bing_search_start", query=query, max_results=max_results)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.base_url,
                    params={"q": query, "count": max_results, "mkt": "pt-BR"},
                    headers={"Ocp-Apim-Subscription-Key": self.api_key}
                )
                response.raise_for_status()
                data = response.json()

                results: List[WebResult] = []
                for item in data.get("webPages", {}).get("value", [])[:max_results]:
                    results.append({
                        "title": item.get("name", "Untitled"),
                        "url": item.get("url", ""),
                        "snippet": item.get("snippet", "")[:500],
                    })

                log.info("bing_search_complete", query=query, count=len(results))
                return results
        except httpx.TimeoutException:
            log.warning("bing_search_timeout", query=query)
            return []
        except httpx.HTTPStatusError as e:
            log.error("bing_search_http_error", query=query, status=e.response.status_code, error=str(e))
            return []
        except Exception as e:
            log.error("bing_search_error", query=query, error=str(e))
            return []

class SerpAPIProvider(WebSearchProvider):
    """SerpAPI Google Search wrapper"""
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://serpapi.com/search"

    async def search(self, query: str, max_results: int = 5) -> List[WebResult]:
        if not settings.web_search_enabled:
            return []

        log.info("serpapi_search_start", query=query, max_results=max_results)
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    self.base_url,
                    params={
                        "q": query,
                        "api_key": self.api_key,
                        "engine": "google",
                        "num": max_results,
                        "gl": "br",
                        "hl": "pt",
                    }
                )
                response.raise_for_status()
                data = response.json()

                results: List[WebResult] = []
                for item in data.get("organic_results", [])[:max_results]:
                    results.append({
                        "title": item.get("title", "Untitled"),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")[:500],
                    })

                log.info("serpapi_search_complete", query=query, count=len(results))
                return results
        except httpx.TimeoutException:
            log.warning("serpapi_search_timeout", query=query)
            return []
        except httpx.HTTPStatusError as e:
            log.error("serpapi_search_http_error", query=query, status=e.response.status_code, error=str(e))
            return []
        except Exception as e:
            log.error("serpapi_search_error", query=query, error=str(e))
            return []

async def get_provider() -> WebSearchProvider:
    """Factory function to return the configured web search provider"""
    provider_name = settings.web_search_provider.lower()
    api_key = settings.web_search_api_key

    if not settings.web_search_enabled:
        log.info("web_search_disabled_using_dummy")
        return DummySearchProvider()

    if provider_name == "tavily":
        if not api_key:
            log.warning("tavily_no_api_key_fallback_to_dummy")
            return DummySearchProvider()
        return TavilySearchProvider(api_key)

    elif provider_name == "bing":
        if not api_key:
            log.warning("bing_no_api_key_fallback_to_dummy")
            return DummySearchProvider()
        return BingSearchProvider(api_key)

    elif provider_name == "serpapi":
        if not api_key:
            log.warning("serpapi_no_api_key_fallback_to_dummy")
            return DummySearchProvider()
        return SerpAPIProvider(api_key)

    else:
        log.info("using_dummy_search_provider", provider=provider_name)
        return DummySearchProvider()
