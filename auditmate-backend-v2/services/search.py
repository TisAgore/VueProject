"""DuckDuckGo web search — инструмент для AI (не требует API-ключа)."""

import asyncio


def _search_sync(query: str, n: int = 5) -> list[dict]:
    """Синхронный поиск (запускается в executor)."""
    try:
        # Пакет переименован в 2025: новый `ddgs`, старый `duckduckgo_search`.
        try:
            from ddgs import DDGS
        except ImportError:
            from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=n))
        return [
            {
                "title":   r.get("title", ""),
                "url":     r.get("href") or r.get("url") or r.get("link") or "",
                "snippet": r.get("body") or r.get("snippet") or r.get("description") or "",
            }
            for r in results
        ]
    except Exception:
        return []


async def web_search(query: str, n: int = 5) -> list[dict]:
    """Async обёртка над синхронным DuckDuckGo поиском."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _search_sync, query, n)
